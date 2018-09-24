"""Plan, PlanStep and Transformation models

This module contains a set of top-level classes that deal with JSON-formatted
plans.

"""

import json
import yaml
import os

import pydent
from pydent import AqSession, models, __version__
from pydent.models import Sample, Item, Plan

class ExternalPlan:
    """Interface for working with the Aquarium Session and Plan models."""
    def __init__(self, aq_plan_name, aq_instance):
        """
        1. Creates a session from stored secrets
        2. Creates a new Plan in the session
        3. Reads in several JSON files for configuring the plan
        4. Creates a few other fields to be populated by inheriting classes

        :param aq_plan_name: name of folder containing configuration files
            Also used as the name of the Plan record in Aquarium
        :type aq_plan_name: str
        :param aq_instance: the instance of Aquarium to use
            Corresponds to a key in the config.yml file
        :type aq_instance: str
        :return: new ExternalPlan
        """
        print("Connecting to Aquarium using pydent version " + str(__version__))
        self.session = ExternalPlan.create_session(aq_instance)
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

    @staticmethod
    def create_session(aq_instance):
        """
        Create a session using credentials in config.yml.
        :param aq_instance: the instance of Aquarium to use
            Corresponds to a key in the config.yml file
        :type aq_instance: str
        :return: new Session
        """
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

        return session

    def get_samples(self, sample_type_name, sample_name, properties={}):
        """
        Searches for a Sample based on name and sample_type. If not found,
        creates a new one and assigns it properties, if present.

        :param sample_type_name: the name of the SampleType
        :type sample_type_name: str
        :param sample_name: the name of the Sample
        :type sample_name: str
        :param properties: additional properties, based on the sample type
        :type properties: dict
        :return: list
        """
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
        """Returns a sorted list of the step_ids found in the plan.json file."""
        return sorted([s.step_id for s in self.steps])

    def step(self, step_id):
        """
        Returns a PlanStep object corresponding to the supplied id.

        :param step_id: the id of the step
        :type step_id: int
        :return: PlanStep
        """
        return next(s for s in self.steps if s.step_id == step_id)

    def create_aq_plan(self):
        """Connects the Plan to the Aq session, then creates the Plan."""
        self.aq_plan.connect_to_session(self.session)
        self.aq_plan.create()

    def update_temp_data_assoc(self, obj, data_associations):
        """
        Adds to a structure that contains data associations that are to be added
        to objects in the Plan once it is created.

        :param obj: the object that the data associations are to be added to
            can be any object inheriting pydent.models.DataAssociatorMixin
        :type obj: Collection, Item, Operation, Plan
        :param data_associations: the key-value pairs to be added to the temp
        :type data_associations: dict
        """
        tdas = [a for a in self.temp_data_associations if a['object'] == obj]

        if tdas:
            tda = tdas[0]

        else:
            tda = { 'object': obj }
            self.temp_data_associations.append(tda)

        tda.update(data_associations)

    def add_data_associations(self):
        """
        Iterates over self.temp_data_associations and adds each data association
        to the indicated object.
        """
        for tda in self.temp_data_associations:
            obj = tda.pop('object')
            for key, value in tda.items():
                obj.associate(key, value)


class PlanStep:
    """A list of transformations that occur simultaneously in the Plan."""
    def __init__(self, plan, plan_step):
        """
        All the important functions happen in inheriting classes.

        :param plan: the ExternalPlan (not the Aquarium Plan)
        :type plan: ExternalPlan
        :param plan_step: a JSON object containing the step configuration
        :type plan_step: dict
        :return: new PlanStep
        """
        self.plan = plan
        self.plan_step = plan_step
        self.transformations = []

    def get_inputs(self, sample_type_name):
        """
        Returns a list of unique inputs of a specified SampleType.

        :param sample_type_name: the name of the SampleType
        :type sample_type_name: str
        :return: list
        """
        sample_type_inputs = []

        for upi in self.uniq_plan_inputs():
            obj = self.plan.input_samples.get(upi)

            if isinstance(obj, Sample):
                this_st_name = obj.sample_type.name

            elif isinstance(obj, Item):
                this_st_name = obj.sample.sample_type.name

            if this_st_name == sample_type_name:
                    sample_type_inputs.append(upi)

        return sample_type_inputs

    def uniq_plan_inputs(self):
        """Returns a list of unique inputs used throughout the PlanStep."""
        plan_inputs = [t.source_samples() for t in self.transformations]
        plan_inputs = [i for i in PlanStep.flatten_list(plan_inputs)]
        return sorted(list(set(plan_inputs)))

    @staticmethod
    def flatten_list(nested_list):
        """
        Flattens a list of lists by one level.

        :param nested_list: the list to be flattened:
        :type nested_list: list
        :return: list
        """
        flattened = []

        for element in nested_list:
            if isinstance(element, list):
                flattened += element

            else:
                flattened.append(element)

        return flattened


class Transformation:
    """
    Contains specifications for converting one sample (the "primary sample")
    into another. Generally does not allow any branching of the primary sample.
    """
    def __init__(self, plan_step, transformation):
        self.plan_step = plan_step
        self.plan = self.plan_step.plan
