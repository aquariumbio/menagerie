import json
import re
import os

import pydent
from pydent import models
from pydent.models import Sample

from plans import ExternalPlan, PlanStep, Transformation
from prot_stab_legs import OvernightLeg, NaiveLeg, InductionLeg, MixCulturesLeg
from prot_stab_legs import SortLeg, FlowLeg, ProtStabLeg
from dna_seq_legs import ExtractDNALeg, QPCRLeg, DiluteLibraryLeg

class XPlan(ExternalPlan):
    """
    Interface for working with the Aquarium Session and Plan models.
    Uses JSON schema derived from SIFT's XPlan schema.
    """
    def __init__(self, aq_plan_name, aq_instance):
        """
        In addition to super(), populates self.steps with new instances
        of PlanStep (YeastDisplayStep or DNASeqStep).

        :param aq_plan_name: name of folder containing configuration files
            Also used as the name of the Plan record in Aquarium
        :type aq_plan_name: str
        :param aq_instance: the instance of Aquarium to use
            Corresponds to a key in the config.yml file
        :type aq_instance: str
        :return: new XPlan
        """
        super().__init__(aq_plan_name, aq_instance)

        # Create PlanStep objects based on operator type
        for s in self.plan['steps']:
            step_type = s["operator"]["type"]

            if step_type == "protstab_round":
                step = YeastDisplayStep(self, s)

            elif step_type == "dna_seq":
                step = DNASeqStep(self, s)

            self.steps.append(step)

        # Find input samples that are likely to vary between operations.
        # TODO: This should be harmonized with the plan_params['operation_defaults'] structure
        for key, sample_data in self.plan_params['input_samples'].items():
            # Special case:
            # Libraries that are combined at the beginning of the Plan.
            if key == "library_composition":
                sample_ids = sample_data["components"]
                component_samples = []

                for sid in sample_ids:
                    component_samples.append(self.find_input_sample(sid))

                sample_data["components"] = component_samples
                self.add_input_sample(key, sample_data)

            # Special case:
            # Collect all of the outputs of an already-run Plan.
            elif key == "plan_outputs":
                plan = self.session.Plan.find(sample_data["plan_id"])
                ops = plan.operations

                ot_name = sample_data["operation_type"]
                ops = [op for op in ops if op.operation_type.name == ot_name]

                for op in ops:
                    item = op.output(sample_data["output"]).item
                    self.add_input_sample(op.id, item)

            # A list of Samples.
            elif isinstance(sample_data, list):
                found_input = []

                for d in sample_data:
                    found_input.append(self.find_input_sample(d))

                self.add_input_sample(key, found_input)

            # A single Sample.
            else:
                found_input = self.find_input_sample(sample_data)
                self.add_input_sample(key, found_input)

        # Get the list of samples for NGS
        # Assumes that there is only one source and only one dna_seq_step
        self.ngs_samples = self.dna_seq_steps()[0].measured_samples

    def get_steps_by_type(self, type):
        """
        Return PlanStep objects based on operator type.

        :param type: the operator type
        :type type: str
        :return: list
        """
        return [s for s in self.steps if s.operator_type == type]

    def provision_steps(self):
        """Get PlanSteps of operator type 'provision'."""
        return self.get_steps_by_type('provision')

    def dna_seq_steps(self):
        """Get PlanSteps of operator type 'dna_seq'."""
        return self.get_steps_by_type('dna_seq')

    def step_ids(self, steps=None):
        """
        Get a sorted list of the step ids in the ExternalPlan.
        Can be for a subset of steps if they are passed.
        """
        steps = steps or self.steps
        return sorted([s.step_id for s in steps])

    def prov_protease_inputs(self):
        """
        Return a dup of self.input_samples with only the proteases.

        :return: dict
        """
        return {k:s for (k,s) in self.input_samples.items() if self.protease_sample(s)}

    def protease_sample(self, s):
        """
        Test whether an object is a Sample of SampleType "Protease."

        :param s: the object to be tested
        :type s: object
        :return: boolean
        """
        return isinstance(s, Sample) and s.sample_type.name == "Protease"

    # Appears dead.
    # def get_provisioned(self, unprovisioned):
    #     txns = self.provision_steps()[0].transformations
    #     provisioned = [t for t in txns if t.source[0]['sample'] == unprovisioned][0]
    #     return provisioned.destination[0]['sample']


class XPlanStep(PlanStep):
    def __init__(self, plan, plan_step):
        super().__init__(plan, plan_step)
        self.plan = plan
        self.plan_step = plan_step

        self.step_id = self.plan_step['id']
        self.name = self.plan_step['name']
        self.operator = self.plan_step['operator']
        self.operator_type = self.operator['type']

        self.transformations = []
        for txn in self.operator.get('transformations', []):
            self.transformations.append(XPlanTransformation(self, txn))

        self.measurements = []
        for msmt in self.operator.get('measurements', []):
            self.measurements.append(XPlanMeasurement(self, msmt))

        self.measured_samples = [m.source for m in self.measurements]

        self.output_operations = {}


    def yeast_inputs(self):
        """
        Get all the inputs that are a type of yeast.

        :return: list
        """
        yeast_sample_types = ["DNA Library", "Yeast Strain", "Yeast Library in Soln 1"]
        yeast_inputs = []

        for st in yeast_sample_types:
            yeast_inputs.extend(self.get_inputs(st))

        return yeast_inputs

    # TODO: Output Operations are handled differently in pup_plans. Harmonize.
    def add_output_operation(self, uri, op):
        """Adds an Operation to the list of output operations for the PlanStep."""
        self.output_operations[uri] = op

    # Appears dead.
    # TODO: Need to make this sort for the GUI layout.
    # def get_sorted_transformations(self):
    #     txns = self.operator.get('transformations')
    #     return txns


class DNASeqStep(XPlanStep):
    def __init__(self, plan, plan_step):
        super().__init__(plan, plan_step)

    def create_step(self, cursor):
        n = 0

        qpcr_2_forward_primer = self.plan.session.Sample.find_by_name("forward primer")
        qpcr_2_reverse_primers = self.plan.input_samples["qpcr_2_reverse_primers"]

        # This is kinda hacky because it doesn't filter for yeast library items
        for _, item in self.plan.input_samples.items():
            if n > 2: break
            extract_leg = ExtractDNALeg(self, cursor)
            extract_leg.set_yeast_from_sample(item.sample)
            extract_leg.add()
            input_op = extract_leg.get_input_op()

            print("Attempting to set fv for %d" % item.id)
            try:
                input_op.set_field_value("Yeast Library", "input", item=item)
            except:
                print("Failed to set fv for %d" % item.id)

            item_id = input_op.input("Yeast Library").item.id
            print("Set fv for %d" % item_id)
            print()

            upstr_op = extract_leg.get_output_op()

            for opt in ["qPCR1", "qPCR2"]:
                qpcr_leg = QPCRLeg(self, cursor)
                qpcr_leg.set_yeast_from_sample(item.sample)
                io_obj = { "Program": opt }

                if opt == "qPCR2":
                    io_obj["Forward/Universal Primer"] = qpcr_2_forward_primer
                    io_obj["Reverse/Barcoded Primer"] = qpcr_2_reverse_primers.pop(0)

                qpcr_leg.set_sample_io(io_obj)
                qpcr_leg.add(opt)

                dnstr_op = qpcr_leg.get_input_op()
                qpcr_leg.wire_ops(upstr_op, dnstr_op)
                upstr_op = qpcr_leg.get_output_op()

            dilute_leg = DiluteLibraryLeg(self, cursor)
            dilute_leg.set_yeast_from_sample(item.sample)
            dilute_leg.add()

            dnstr_op = dilute_leg.get_input_op()
            dilute_leg.wire_ops(upstr_op, dnstr_op)

            cursor.incr_x()
            cursor.return_y()
            n += 1


class YeastDisplayStep(XPlanStep):
    def __init__(self, plan, plan_step):
        super().__init__(plan, plan_step)

    def create_step(self, cursor, start_date):
        # TODO: Do this in a way that doesn't depend on starting at 1.
        if int(self.step_id) > 1:
            prev_plan_step = self.plan.step(self.step_id - 1)
            prev_step_outputs = prev_plan_step.output_operations
        else:
            prev_step_outputs = {}

        new_inputs = {}

        for input_yeast in self.yeast_inputs():
            st_name = self.plan.input_samples[input_yeast].sample_type.name
            is_library = st_name == 'DNA Library'

            if not prev_step_outputs.get(input_yeast):
                cursor.incr_y(2)
                container_opt = 'library start' if is_library else 'control'

                overnight_samples = []
                library_composition = self.plan.input_samples.get("library_composition")
                mix_cultures = is_library and library_composition

                if mix_cultures:
                    cursor.incr_y()
                    for comp in library_composition["components"]:
                        overnight_samples.append(comp)

                else:
                    overnight_samples.append(self.plan.input_samples[input_yeast])

                overnight_ops = {}

                for os in overnight_samples:
                    overnight_leg = OvernightLeg(self, cursor)
                    overnight_leg.set_yeast_from_sample(os)
                    overnight_leg.add(container_opt)

                    subs = (input_yeast, str(start_date.date()))
                    overnight_leg.set_start_date(start_date.date())

                    overnight_ops[os.name] = overnight_leg.get_innoculate_op()
                    print("Planning innoculation of %s on %s" % subs)

                    cursor.incr_x()
                    cursor.incr_y()

                if mix_cultures:
                    cursor.decr_y()
                    cursor.return_x()
                    mix_cultures_leg = MixCulturesLeg(self, cursor)
                    mix_cultures_leg.set_yeast(input_yeast)
                    mix_cultures_leg.set_components(library_composition)
                    mix_cultures_leg.add(container_opt)

                    mix_cultures_op = mix_cultures_leg.select_op('Mix Cultures')
                    culture_inputs = mix_cultures_op.input_array("Component Yeast Culture")

                    for culture in culture_inputs:
                        op = overnight_ops[culture.sample.name]
                        mix_cultures_leg.wire_ops(op.output("Yeast Culture"), culture)

                    upstr_op = mix_cultures_op

                else:
                    upstr_op = overnight_leg.select_op('Innoculate Yeast Library')

                cursor.return_y()

                if input_yeast in self.plan.ngs_samples:
                    cursor.decr_y(SortLeg.length() - NaiveLeg.length())
                    naive_leg = NaiveLeg(self, cursor)
                    naive_leg.set_yeast(input_yeast)
                    naive_leg.add('library')
                    cursor.return_y()

                    dnstr_op = naive_leg.select_op('Store Yeast Library Sample')
                    naive_leg.wire_ops(upstr_op, dnstr_op)

                new_inputs[input_yeast] = upstr_op

            upstr_op = prev_step_outputs.get(input_yeast) or new_inputs.get(input_yeast)

            cursor.set_x(upstr_op.x)

            if int(self.step_id) > 1 and is_library:
                cursor.decr_x(2)
            else:
                cursor.incr_x()

            cursor.return_y()

            cursor.incr_y(2)
            container_opt = 'library' if is_library else 'control'
            induction_leg = InductionLeg(self, cursor)
            induction_leg.set_yeast(input_yeast)
            induction_leg.add(container_opt)
            cursor.return_y()

            dnstr_op = induction_leg.select_op('Dilute Yeast Library')
            induction_leg.wire_ops(upstr_op, dnstr_op)

            txns = [t for t in self.transformations if input_yeast in t.source_samples()]

            partitioned = {}

            for t in txns:
                sample = t.protease().get('sample', '')

                if not partitioned.get(sample):
                    partitioned[sample] = []

                partitioned[sample].append(t)

            proteases = list(partitioned.keys())
            proteases.sort()

            for p in proteases:
                txns = partitioned[p]
                txns.sort(key=lambda t: t.protease().get('concentration', 0))

                for txn in txns:
                    src = txn.source
                    for dst in txn.destination:
                        ngs_sample = dst['sample'] in self.plan.ngs_samples
                        if ngs_sample:
                            this_leg = SortLeg(self, cursor)
                        else:
                            this_leg = FlowLeg(self, cursor)

                        this_leg.set_yeast(input_yeast)
                        this_leg.set_protease(src)

                        # This is not a good way to set these variables
                        if ngs_sample:
                            this_leg.sample_io['Control?'] = 'no'
                        else:
                            yeast_name = this_leg.sample_io['Labeled Yeast Library'].name
                            if yeast_name == 'EBY100 + pETcon3':
                                this_leg.sample_io['Control?'] = 'autofluorescence'
                            elif yeast_name == 'AMA1-best':
                                if this_leg.sample_io['Protease Concentration'] == 0:
                                    this_leg.sample_io['Control?'] = 'high-fitc'
                                else:
                                    this_leg.sample_io['Control?'] = 'protease'

                        this_leg.add(container_opt)

                        upstr_op = induction_leg.select_op('Dilute Yeast Library')
                        dnstr_op = this_leg.select_op('Challenge and Label')
                        this_leg.wire_ops(upstr_op, dnstr_op)

                        output_op = this_leg.get_innoculate_op()

                        if output_op:
                            self.add_output_operation(dst['sample'], output_op)
                            self.plan.add_input_sample(dst['sample'], output_op.output('Yeast Culture').sample)

                        cursor.incr_x()
                        cursor.return_y()

                cursor.incr_x(0.25)


class XPlanTransformation(Transformation):
    def __init__(self, plan_step, transformation):
        super().__init__(plan_step, transformation)
        self.source = self.format(transformation['source'])
        self.destination = self.format(transformation['destination'])

    def source_samples(self):
        return [x['sample'] for x in self.source]

    def destination_samples(self):
        return [x['sample'] for x in self.destination]

    def protease(self):
        provisioned = self.plan.prov_protease_inputs()
        proteases = [x for x in self.source if x['sample'] in provisioned.keys()]

        if proteases:
            return proteases[0]
        else:
            return {}

    def yeast(self):
        return [x for x in self.source_samples() if x in self.plan_step.yeast_inputs()]

    @staticmethod
    def format(element):
        if isinstance(element, list):
            return [{ 'sample': e } if isinstance(e, str) else e for e in element]

        elif isinstance(element, dict):
            return [element]

        elif isinstance(element, str):
            return [{ 'sample': element }]

        else:
            raise Exception('Format of %s not recognized' % str(element))


class XPlanMeasurement():
    def __init__(self, plan_step, measurement):
        self.plan_step = plan_step
        self.plan = self.plan_step.plan
        self.source = measurement['source']
        self.file = measurement['file']
