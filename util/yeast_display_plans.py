import json
import re
import os

import pydent
from pydent import models
from pydent.models import Sample, Item

from util.plans import ExternalPlan, PlanStep, Transformation, InputError
from util.yeast_display_legs import OvernightLeg, NaiveLeg, InductionLeg, MixCulturesLeg
from util.yeast_display_legs import SortLeg, FlowLeg, YeastDisplayLeg
from util.dna_seq_legs import ExtractDNALeg, QPCRLeg, DiluteLibraryLeg

class YeastDisplayPlan(ExternalPlan):
    """
    Interface for working with the Aquarium Session and Plan models.
    Originally based on JSON schema derived from SIFT's XPlan schema.
    """
    def __init__(self, plan_path, aq_instance, aq_plan_name=None):
        """
        In addition to super(), populates self.steps with new instances
        of PlanStep (YeastDisplayStep or DNASeqStep).

        :param plan_path: name of folder containing configuration files
            Also used as the name of the Plan record in Aquarium
        :type plan_path: str
        :param aq_instance: the instance of Aquarium to use
            Corresponds to a key in the config.yml file
        :type aq_instance: str
        :return: new YeastDisplayPlan
        """
        super().__init__(plan_path, aq_instance, aq_plan_name)

        # Get the list of samples for NGS
        # Assumes that there is only one source and only one dna_seq_step
        # TODO: This method is not great.
        self.ngs_sample_keys = []
        for step in self.dna_seq_steps():
            for source in step.measured_samples:
                self.ngs_sample_keys.append(source.get("sample_key"))

    def initialize_step(self, step_data):
        super().initialize_step(step_data)

        step_type = step_data["type"]

        if step_type == "protstab_round" or step_type == "yeast_display_round":
            step = YeastDisplayStep(self, step_data)

        elif step_type == "dna_seq":
            step = DNASeqStep(self, step_data)
        
        else:
            step = YeastDisplayPlanStep(self, step_data)

        return step

    def dna_seq_steps(self):
        """Get PlanSteps of operator type 'dna_seq'."""
        return self.get_steps_by_type('dna_seq')

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


class YeastDisplayPlanStep(PlanStep):
    def __init__(self, plan, plan_step):
        super().__init__(plan, plan_step)
        self.plan = plan
        self.plan_step = plan_step

        self.step_id = self.plan_step['id']
        self.operator = self.plan_step['operator']
        self.operator_type = self.type
        self.name = self.plan_step['name']

        self.transformations = []
        for txn in self.operator.get('transformations', []):
            self.transformations.append(YeastDisplayPlanTransformation(self, txn))

        self.measurements = []
        for msmt in self.operator.get('measurements', []):
            self.measurements.append(YeastDisplayPlanMeasurement(self, msmt))

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

    # TODO: Output Operations are handled differently in cloning_plans. Harmonize.
    def add_output_operation(self, uri, op):
        """Adds an Operation to the list of output operations for the PlanStep."""
        self.output_operations[uri] = op

    @staticmethod
    def sample_key(element):
        return element.get('sample') or element.get('sample_key')


class DNASeqStep(YeastDisplayPlanStep):

    valid_templates = ["DNA Library"]

    def __init__(self, plan, plan_step):
        super().__init__(plan, plan_step)

        if not self.transformations:
            self.create_transformations_from_params()

    def create_transformations_from_params(self):
        input_samples = self.plan.input_samples
        qpcr_2_reverse_primers = input_samples.get("qpcr_2_reverse_primers")
        qpcr_2_forward_primer = input_samples.get("qpcr_2_forward_primer")

        template_items = [i for i in input_samples.values() if self.istemplate(i)]
        template_items.sort(key=lambda i: i.id)

        for i, template_item in enumerate(template_items):
            txn = {
                "source": [
                    {
                        "input_name": "Template",
                        "item": template_item
                    },
                    {
                        "input_name": "Forward Primer",
                        "sample": qpcr_2_forward_primer,
                        "sample_key": "qpcr_2_forward_primer"
                    },
                    {
                        "input_name": "Reverse Primer",
                        "sample": qpcr_2_reverse_primers[i],
                        "sample_key": "qpcr_2_reverse_primer"
                    }
                ],
                "destination": [

                ]
            }
            self.transformations.append(YeastDisplayPlanTransformation(self, txn))

    @staticmethod
    def istemplate(item):
        return isinstance(item, Item) and item.sample.sample_type.name in DNASeqStep.valid_templates

    def create_step(self, cursor):
        for txn in self.transformations:
            template_source = [s for s in txn.source if s["input_name"] == "Template"][0]

            if template_source.get("item"):
                library_item = template_source["item"]
            elif template_source.get("item_id"):
                library_item = self.plan.session.Item.find(template_source["item_id"])
            else:
                raise InputError("Unable to identify Item for source: " + template_source)

            library_sample = library_item.sample

            extract_leg = ExtractDNALeg(self, cursor)
            extract_leg.set_yeast_from_sample(library_sample)
            extract_leg.add()
            input_op = extract_leg.get_input_op()

            # print("Attempting to set fv for %d" % library_item.id)
            try:
                input_op.set_field_value("Yeast Library", "input", item=library_item)
            except:
                print("Failed to set fv for %d" % library_item.id)

            upstr_op = extract_leg.get_output_op()

            for opt in ["qPCR1", "qPCR2"]:
                io_obj = { "Program": opt }

                if opt == "qPCR1":
                    plates = False

                elif opt == "qPCR2":
                    plates = True

                    fwd_primer_src = [s for s in txn.source if s.get("sample_key") == "qpcr_2_forward_primer"][0]
                    fwd_primer = fwd_primer_src.get("sample") or self.plan.session.Sample.find_by_name(fwd_primer_src["name"])
                    io_obj["Forward Primer"] = fwd_primer

                    rev_primer_src = [s for s in txn.source if s.get("sample_key") == "qpcr_2_reverse_primer"][0]
                    rev_primer = rev_primer_src.get("sample") or self.plan.session.Sample.find_by_name(rev_primer_src["name"])
                    io_obj["Reverse Primer"] = rev_primer

                qpcr_leg = QPCRLeg(self, cursor, plates)
                qpcr_leg.set_yeast_from_sample(library_sample)

                qpcr_leg.set_sample_io(io_obj)
                qpcr_leg.add(opt)

                dnstr_op = qpcr_leg.get_input_op()
                qpcr_leg.wire_ops(upstr_op, dnstr_op)
                upstr_op = qpcr_leg.get_output_op()

            dilute_leg = DiluteLibraryLeg(self, cursor)
            dilute_leg.set_yeast_from_sample(library_sample)
            dilute_leg.add()

            dnstr_op = dilute_leg.get_input_op()
            dilute_leg.wire_ops(upstr_op, dnstr_op)

            cursor.incr_x()
            cursor.return_y()
        
        cursor.update_max_x()


class YeastDisplayStep(YeastDisplayPlanStep):
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
            st_name = self.plan.input_sample(input_yeast).sample_type.name
            is_library = st_name == 'DNA Library'

            if not prev_step_outputs.get(input_yeast):
                cursor.incr_y(2)
                container_opt = 'library_start' if is_library else 'control'

                overnight_samples = []
                library_composition = self.plan.input_sample("library_composition")
                mix_cultures = is_library and library_composition

                if mix_cultures:
                    cursor.incr_y()
                    for comp in library_composition["components"]:
                        overnight_samples.append(comp)

                else:
                    overnight_samples.append(self.plan.input_sample(input_yeast))

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

                if input_yeast in self.plan.ngs_sample_keys:
                    cursor.decr_y(SortLeg.length() - NaiveLeg.length())
                    cursor.decr_x()
                    naive_leg = NaiveLeg(self, cursor)
                    naive_leg.set_yeast(input_yeast)
                    naive_leg.add('library')
                    cursor.incr_x()
                    cursor.return_y()

                    dnstr_op = naive_leg.select_op('Store Yeast Library Sample')
                    naive_leg.wire_ops(upstr_op, dnstr_op)

                new_inputs[input_yeast] = upstr_op

            upstr_op = prev_step_outputs.get(input_yeast) or new_inputs.get(input_yeast)

            # cursor.set_x(round(upstr_op.x/cursor.x_incr))

            if int(self.step_id) > 1 and is_library:
                # cursor.decr_x(2)
                temp_ops = [op for op in self.plan.aq_plan.operations if op.y <= cursor.y]
                current_x = max([op.x for op in temp_ops] or [cursor.x_home])
            else:
                current_x = upstr_op.x

            cursor.set_x(round(current_x/cursor.x_incr))
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
                    for dst in txn.destination_samples():
                        ngs_sample = dst in self.plan.ngs_sample_keys
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
                            if yeast_name in ['EBY100 + pETcon3', 'EBY100 + PETCONv3_baker']:
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
                            self.add_output_operation(dst, output_op)
                            self.plan.add_input_sample(dst, output_op.output('Yeast Culture').sample)

                        cursor.incr_x()
                        cursor.return_y()

                cursor.incr_x()

        cursor.update_max_x()
        cursor.decr_y(SortLeg.length() + 3)
        cursor.set_y_home()


class YeastDisplayPlanTransformation(Transformation):
    def __init__(self, plan_step, transformation):
        super().__init__(plan_step, transformation)
        self.source = self.format(transformation['source'])
        self.destination = self.format(transformation['destination'])

    def source_samples(self):
        return [self.sample_key(x) for x in self.source]

    def destination_samples(self):
        return [self.sample_key(x) for x in self.destination]

    def protease(self):
        provisioned = self.plan.prov_protease_inputs()
        proteases = [x for x in self.source if self.sample_key(x) in provisioned.keys()]

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

    @staticmethod
    def sample_key(element):
        return YeastDisplayPlanStep.sample_key(element)


class YeastDisplayPlanMeasurement():
    def __init__(self, plan_step, measurement):
        self.plan_step = plan_step
        self.plan = self.plan_step.plan
        self.source = measurement['source']
        self.file = measurement.get('file')
