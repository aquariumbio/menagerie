import json
import yaml
import os

import pydent
from pydent import AqSession, models
from pydent.models import Sample, Plan

class ExternalPlan:
    def __init__(self, aq_plan_name, plan_path, plan_defaults_path, config_path):
        self.set_session(config_path)
        self.aq_plan = Plan(name=aq_plan_name)

        with open(plan_path, 'r') as f:
            self.plan = json.load(f)

        with open(plan_defaults_path, 'r') as f:
            plan_defaults = json.load(f)

            self.defaults = plan_defaults.get('defaults') or []

            for op_default in self.defaults:
                for key, value in op_default['defaults'].items():
                    samples = self.session.Sample.where({ 'name': value })
                    if samples:
                        op_default['defaults'][key] = samples[0]

            self.steps = []
            self.input_samples = {}

    def set_session(self, config_path):
        with open(config_path, 'r') as f:
            config = yaml.load(f)

        nursery = config['aquarium']['nursery']

        session = AqSession(
                nursery['username'],
                nursery['password'],
                nursery['url']
                )

        # Test the session
        me = session.User.where({'login': nursery['username']})[0]
        print('Logged in as %s\n' % me.name)

        self.session = session

    def get_samples(self, sample_type_name, sample_name):
        st = self.session.SampleType.where({ 'name': sample_type_name })[0]
        aq_samples = self.session.Sample.where({
            'name': sample_name,
            'sample_type_id': st.id
        })

        if not aq_samples:
            s = Sample(
                name=sample_name,
                project='SD2',
                sample_type_id=st.id
            )

            s.connect_to_session(self.session)
            s.save()

            aq_samples = [s]

        return aq_samples

    def step_ids(self):
        return sorted([s.step_id for s in self.steps])

    def step(self, step_id):
        return next(s for s in self.steps if s.step_id == step_id)

    def launch_aq_plan(self):
        self.aq_plan.connect_to_session(self.session)
        self.aq_plan.create()


class PlanStep:
    def __init__(self, plan, plan_step):
        self.plan = plan
        self.plan_step = plan_step
        self.transformations = []

    # Possibly dead code
    def get_transformations_by_input(self, input):
        txns = self.transformations
        return [t for t in txns if input in t.source_samples()]

    def uniq_plan_inputs(self):
        plan_inputs = [t.source_samples() for t in self.transformations]
        plan_inputs = [i for i in self.flatten_list(plan_inputs)]
        return sorted(list(set(plan_inputs)))

    def get_inputs(self, sample_type_name):
        sample_type_inputs = []
        upis = self.uniq_plan_inputs()

        for u in upis:
            sample = self.plan.input_samples.get(u)

            if sample and sample.sample_type.name == sample_type_name:
                sample_type_inputs.append(u)

        return sample_type_inputs

    @staticmethod
    def flatten_list(nested_list):
        flattened = []

        for element in nested_list:
            if isinstance(element, list):
                flattened += element

            else:
                flattened.append(element)

        return flattened


class Transformation:
    def __init__(self, plan_step, transformation):
        self.plan_step = plan_step
        self.plan = self.plan_step.plan
