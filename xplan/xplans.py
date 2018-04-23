import json
import re

from plans import ExternalPlan, PlanStep, Transformation

import pydent
from pydent import models
from pydent.models import Sample

class XPlan(ExternalPlan):
    def __init__(self, aq_plan_name, plan_path, plan_defaults_path, config_path):
        super().__init__(aq_plan_name, plan_path, plan_defaults_path, config_path)

        self.steps = [XPlanStep(self, s) for s in self.plan['steps']]

        with open(plan_defaults_path, 'r') as f:
            plan_defaults = json.load(f)

            # This is unique to protein stability and should be moved
            self.concentrations = plan_defaults['concentrations']

            self.input_samples = {}
            for txn in self.provision_steps()[0].transformations:
                dst_uri = txn.destination[0]['sample']
                src_uri = txn.source[0]['sample']
                sample = self.session.Sample.find(plan_defaults['input_samples'][src_uri])
                self.add_input_sample(dst_uri, sample)

        # Assumes that there is only one source and only one dna_seq_step
        self.ngs_samples = self.dna_seq_steps()[0].measured_samples

        self.set_default_protease()

    def add_input_sample(self, uri, sample):
        self.input_samples[uri] = sample

    def get_steps_by_type(self, type):
        return [s for s in self.steps if s.operator_type == type]

    def provision_steps(self):
        return self.get_steps_by_type('provision')

    def dna_seq_steps(self):
        return self.get_steps_by_type('dna_seq')

    def step_ids(self, steps=None):
        steps = steps or self.steps
        return sorted([s.step_id for s in steps])

    ##### These are probably unique to protein stability #####

    def protstab_round_steps(self):
        return self.get_steps_by_type('protstab_round')

    def set_default_protease(self):
        def_prot_pat = re.compile(r'protease_2', re.IGNORECASE)

        possible_defaults = self.protease_inputs()
        test = [s for s in possible_defaults if re.search(def_prot_pat, s)]

        if test:
            unprovisioned = test[0]

        else:
            unprovisioned = possible_defaults[0]

        txns = self.provision_steps()[0].transformations
        provisioned = [t for t in txns if t.source[0]['sample'] == unprovisioned][0]
        self.default_protease = provisioned.destination[0]['sample']

    def protease_inputs(self):
        protease_inputs = []
        prot_pat = re.compile(r'protease', re.IGNORECASE)

        for t in self.provision_steps()[0].transformations:
            for s in t.source:
                if re.search(prot_pat, s['sample']):
                    protease_inputs.append(s['sample'])

        return list(set(protease_inputs))


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
            self.transformations.append(XPlanTransformation(txn))

        self.measurements = []
        for msmt in self.operator.get('measurements', []):
            self.measurements.append(XPlanMeasurement(msmt))

        self.measured_samples = [m.source for m in self.measurements]

        # self.flow_samples = [m.source for m in self.measurements if m.file.endswith('.fcs')]

    # TODO: Need to make this sort for the GUI layout.
    def get_sorted_transformations(self):
        txns = self.operator.get('transformations')
        return txns


class XPlanTransformation(Transformation):
    def __init__(self, transformation):
        super().__init__(transformation)
        self.source = self.format(transformation['source'])
        self.destination = self.format(transformation['destination'])

    def source_samples(self):
        return [x['sample'] for x in self.source]

    def destination_samples(self):
        return [x['sample'] for x in self.destination]

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
    def __init__(self, measurement):
        self.source = measurement['source']
        self.file = measurement['file']
