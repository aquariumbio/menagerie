import json
import yaml
import os

import pydent
from pydent import AqSession, models, __version__
from pydent.models import Sample, Plan

class ExternalPlan:
    def __init__(self, aq_plan_name, aq_instance):
        print("pydent version: " + str(__version__))
        self.set_session(aq_instance)
        self.aq_plan = Plan(name=aq_plan_name)
        self.plan_path = "plans/%s" % aq_plan_name

        plan_file = os.path.join(self.plan_path, 'plan.json')
        with open(plan_file, 'r') as f:
            self.plan = json.load(f)

        # TODO: Unify the structure of 'aquarium_defaults.json' and "params_%s.json"
        aq_defaults_file = os.path.join(self.plan_path, 'aquarium_defaults.json')
        with open(aq_defaults_file, 'r') as f:
            self.aq_defaults = json.load(f)

        plan_params_file = "params_%s.json" % aq_instance
        plan_params_file = os.path.join(self.plan_path, plan_params_file)
        with open(plan_params_file, 'r') as f:
            self.plan_params = json.load(f)

            self.defaults = self.plan_params.get('operation_defaults', [])

            for op_default in self.defaults:
                for key, value in op_default['defaults'].items():
                    samples = self.session.Sample.where({ 'name': value })
                    if samples:
                        op_default['defaults'][key] = samples[0]

        self.steps = []
        self.input_samples = {}

        self.temp_data_associations = []

    def set_session(self, aq_instance):
        with open('config.yml', 'r') as f:
            config = yaml.load(f)

        login = config['aquarium'][aq_instance]

        session = AqSession(
            login['username'],
            login['password'],
            login['url']
        )

        # Test the session
        me = session.User.where({'login': login['username']})[0]
        print('Logged in as %s\n' % me.name)

        self.session = session

    def get_samples(self, sample_type_name, sample_name, properties={}):
        st = self.session.SampleType.where({ 'name': sample_type_name })[0]
        aq_samples = self.session.Sample.where({
            'name': sample_name,
            'sample_type_id': st.id
        })

        if not aq_samples:
            allowable_properties = {}

            if properties:
                for ft in st.field_types:
                    prop = properties.get(ft.name)
                    if prop:
                        if ft.ftype == 'sample':
                            prop = self.session.Sample.find_by_name(prop)

                        allowable_properties[ft.name] = prop

            s = self.session.Sample.new(
                name=sample_name,
                project='SD2',
                sample_type_id=st.id,
                properties=allowable_properties
            )

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

    def update_temp_data_assoc(self, obj, data_associations):
        tdas = [a for a in self.temp_data_associations if a['object'] == obj]

        if tdas:
            tda = tdas[0]

        else:
            tda = { 'object': obj }
            self.temp_data_associations.append(tda)

        tda.update(data_associations)

    def add_data_associations(self):
        for tda in self.temp_data_associations:
            obj = tda.pop('object')
            for key, value in tda.items():
                obj.associate(key, value)


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
