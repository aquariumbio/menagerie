import json

import pydent
from pydent import models
from pydent.models import Sample

import plans
from plans import ExternalPlan, PlanStep

class PupPlan(ExternalPlan):

    input_list_names = ['partSamples', 'vectorSamples']
    txn_list_names = ['designs']

    def __init__(self, aq_plan_name, aq_instance):
        super().__init__(aq_plan_name, aq_instance)

        for list_name in PupPlan.input_list_names:
            for sample in self.plan[list_name]:
                sample['aqSamples'] = self.get_samples('Fragment', sample['name'])
                self.input_samples[sample['name']] = sample['aqSamples'][0]

        # Not sure why this loop is happening.
        for list_name in PupPlan.txn_list_names:
            step_id = len(self.steps) + 1
            step = PupPlanStep(self, self.plan[list_name], step_id)
            self.steps.append(step)

            for txn in step.transformations:
                for sample_name in txn['destination']:
                    samples = self.get_samples('Plasmid', sample_name)
                    self.input_samples[sample_name] = samples[0]


class PupPlanStep(PlanStep):
    def __init__(self, plan, plan_step, step_id):
        super().__init__(plan, plan_step)
        self.plan = plan
        self.plan_step = plan_step
        self.step_id = step_id

        self.transformations = []
        for d in plan_step:
            txn = {'destination': [d['name']] }
            src = list(d['partPositionMap'].values())
            src.append(d['vectorName'])
            txn['source'] = src
            self.transformations.append(txn)

        self.operator_type = self.plan.plan['parameters']['buildMethod']
