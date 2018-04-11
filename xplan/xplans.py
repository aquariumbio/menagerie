import json

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
            for uri, sample_id in plan_defaults['input_samples'].items():
                self.input_samples[uri] = self.session.Sample.find(sample_id)

    ##### These are probably unique to protein stability #####

    def ngs_samples(self):
        ngs_map = [x.measurements for x in self.steps if x.operator_type == 'dna_seq'][0]
        return [x['source'] for x in ngs_map]

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
        self.operator = self.plan_step['operator']
        self.operator_type = self.operator['type']

        self.transformations = self.operator.get('transformations')

        self.measurements = self.operator.get('measurements')

    # TODO: Need to make this sort for the GUI layout.
    def get_sorted_transformations(self):
        txns = self.operator.get('transformations')
        return txns
