import json
import re
import os

import pydent
from pydent import models
from pydent.models import Sample

from plans import ExternalPlan, PlanStep, Transformation
from prot_stab_legs import OvernightLeg, NaiveLeg, InductionLeg, MixCulturesLeg
from prot_stab_legs import SortLeg, FlowLeg, ProtStabLeg

class XPlan(ExternalPlan):
    def __init__(self, aq_plan_name, aq_instance):
        super().__init__(aq_plan_name, aq_instance)

        self.steps = [YeastDisplayStep(self, s) for s in self.plan['steps']]

        self.input_samples = {}
        for plan_id, aq_id in self.plan_params['input_samples'].items():
            if plan_id == "library_composition":
                aq_ids = aq_id["components"]
                component_samples = []

                for ai in aq_ids:
                    component_samples.append(self.find_input_sample(ai))

                aq_id["components"] = component_samples
                found_input = aq_id

            else:
                found_input = self.find_input_sample(aq_id)

            self.add_input_sample(plan_id, found_input)

        # Assumes that there is only one source and only one dna_seq_step
        self.ngs_samples = self.dna_seq_steps()[0].measured_samples

    def find_input_sample(self, aq_id):
        if isinstance(aq_id, int):
            attr = 'id'
        else:
            attr = 'name'

        return self.session.Sample.where({attr: aq_id})[0]

    def add_input_sample(self, plan_id, sample):
        self.input_samples[plan_id] = sample

    def get_steps_by_type(self, type):
        return [s for s in self.steps if s.operator_type == type]

    def provision_steps(self):
        return self.get_steps_by_type('provision')

    def dna_seq_steps(self):
        return self.get_steps_by_type('dna_seq')

    def step_ids(self, steps=None):
        steps = steps or self.steps
        return sorted([s.step_id for s in steps])

    def protease_sample(self, s):
        return isinstance(s, Sample) and s.sample_type.name == "Protease"

    def prov_protease_inputs(self):
        return {k:s for (k,s) in self.input_samples.items() if self.protease_sample(s)}

    def get_provisioned(self, unprovisioned):
        txns = self.provision_steps()[0].transformations
        provisioned = [t for t in txns if t.source[0]['sample'] == unprovisioned][0]
        return provisioned.destination[0]['sample']


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
        yeast_handles = ["DNA Library", "Yeast Strain"]
        yeast_inputs = []

        for h in yeast_handles:
            yeast_inputs.extend(self.get_inputs(h))

        return yeast_inputs

    def add_output_operation(self, uri, op):
        self.output_operations[uri] = op

    # TODO: Need to make this sort for the GUI layout.
    def get_sorted_transformations(self):
        txns = self.operator.get('transformations')
        return txns


class YeastDisplayStep(XPlanStep):
    def __init__(self, plan, plan_step):
        super().__init__(plan, plan_step)

    def create_step(self, cursor, start_date):
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
