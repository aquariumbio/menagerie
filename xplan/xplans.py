import json
import re

from plans import ExternalPlan, PlanStep

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
            # for uri, sample_id in plan_defaults['input_samples'].items():
            #     self.input_samples[uri] = self.session.Sample.find(sample_id)
            sids = plan_defaults['input_samples']
            for txn in self.provision_steps()[0].transformations:
                dst_uri = txn['destination']
                src_uri = txn['source']
                sample = self.session.Sample.find(sids[src_uri])
                self.input_samples[dst_uri] = sample

        self.set_default_protease()

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

    def ngs_samples(self):
        ngs_map = [x.measurements for x in self.dna_seq_steps()][0]
        return [x['source'] for x in ngs_map]

    def set_default_protease(self):
        pat = re.compile(r'(?<!chymo)trypsin', re.IGNORECASE)
        txns = self.provision_steps()[0].transformations
        self.default_protease = [t['destination'] for t in txns if re.search(pat, t['source'])][0]

    def get_concentration(self, key):
        return self.concentrations.get(key) or self.concentrations.get('default')

    def get_treatment_key(destination):
        return destination.split('/')[-1]


class XPlanStep(PlanStep):
    def __init__(self, plan, plan_step):
        super().__init__(plan, plan_step)
        self.plan = plan
        self.plan_step = plan_step

        self.step_id = self.plan_step['id']
        self.name = self.plan_step['name']
        self.operator = self.plan_step['operator']
        self.operator_type = self.operator['type']

        self.transformations = self.operator.get('transformations')

        self.measurements = self.operator.get('measurements')

    # TODO: Need to make this sort for the GUI layout.
    def get_sorted_transformations(self):
        txns = self.operator.get('transformations')
        return txns
