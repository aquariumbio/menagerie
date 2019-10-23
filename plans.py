"""Plan, PlanStep, Transformation, Leg, and Cursor models

This module contains a set of top-level classes that deal with JSON-formatted
plans.

"""

import json
import yaml
import os
import copy

import pydent
from pydent import AqSession, models, __version__
from pydent.models import Sample, Item, Plan
from pydent.exceptions import AquariumModelError

def get_obj_by_name(leg, name):
    ops = [x for x in leg if x["name"] == name]
    if ops: return ops[0]

class ExternalPlan:
    """Interface for working with the Aquarium Session and Plan models."""
    def __init__(self, aq_plan_name, aq_instance):
        """
        1. Creates a session from stored secrets
        2. Creates a new Plan in the session
        3. Reads in several JSON files for configuring the plan
        4. Populates self.defaults with found samples
        5. Creates a few other fields to be populated by inheriting classes

        :param aq_plan_name: name of folder containing configuration files
            Also used as the name of the Plan record in Aquarium
        :type aq_plan_name: str
        :param aq_instance: the instance of Aquarium to use
            Corresponds to a key in the config.yml file
        :type aq_instance: str
        :return: new ExternalPlan
        """
        self.session = ExternalPlan.create_session(aq_instance)

        self.aq_plan = Plan(name=aq_plan_name)
        self.plan_path = "plans/%s" % aq_plan_name

        self.plan = self.load_json_from_file('plan.json')
        self.aq_defaults = self.load_json_from_file('aquarium_defaults.json')
        self.plan_params = self.load_json_from_file("params_%s.json" % aq_instance)

        self.operation_defaults = self.aq_defaults.get("operation_defaults", [])
        self.defaults = self.operation_defaults
        self.populate_from_database()

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
        dirname = os.path.dirname(__file__)
        filename = os.path.join(dirname, 'config.yml')

        with open(filename, 'r') as f:
            config = yaml.load(f)

        login = config['aquarium'][aq_instance]

        session = AqSession(
            login['username'],
            login['password'],
            login['url']
        )

        # Test the session
        msg = "Connected to Aquarium at {} using pydent version {}"
        print(msg.format(session.url, str(__version__)))

        me = session.User.where({'login': login['username']})[0]
        print('Logged in as {}\n'.format(me.name))

        return session

    def load_json_from_file(self, file_name):
        """
        Loads a file in the plan config path as a JSON object.

        :param file_name: the name of the JSON file to load
        :type file_name: str
        :return: json object
        """
        file_path = os.path.join(self.plan_path, file_name)
        with open(file_path, 'r') as f:
            return json.load(f)

    def populate_from_database(self):
        """
        Parses part of aquarium_defaults.json and finds corresponding 
        records in Aq. Populates the data structure populated with 
        the records.
        """
        for d in self.operation_defaults:
            for role in ["inputs", "outputs"]:
                for io_data in d.get(role, {}).values():
                    sample_name = io_data.get("sample")
                    if sample_name:
                        sample = self.session.Sample.find_by_name(sample_name)
                        if sample:
                            io_data["sample"] = sample
                        else:
                            raise "Input error: {}".format(sample_name)

                    ot_data = io_data.get("object_type")
                    if isinstance(ot_data, str):
                        object_type = self.session.ObjectType.find_by_name(ot_data)
                        if object_type:
                            io_data["object_type"] = object_type
                        else:
                            raise "Input error: {}".format(ot_data)

                    elif isinstance(ot_data, dict):
                        for option, ot_name in ot_data.items():
                            object_type = self.session.ObjectType.find_by_name(ot_name)
                            if object_type:
                                ot_data[option] = object_type
                            else:
                                raise "Input error: {}".format(ot_name)

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

    def find_input_sample(self, aq_id):
        """
        Find a Sample when the attribute can be either id or name.

        :param aq_id: the attribute
        :type aq_id: int or str
        :return: Sample
        """
        if isinstance(aq_id, int):
            attr = 'id'
        else:
            attr = 'name'

        return self.session.Sample.where({attr: aq_id})[0]

    def add_input_sample(self, key, sample):
        """
        Add a sample to self.input_samples.
        :param key: A unique identifer of the Sample
        :type key: str
        :param sample: The Sample to be added
        :type sample: Sample
        """
        self.input_samples[key] = sample

    # TODO: This method seems kind of dumb.
    def get_input_sample(self, sample_name):
        """
        Return the input Sample based on the key. If not found, return the key
        instead.

        :param sample_name: The unique identifier of the Sample
        :type sample_name: str
        :return: Sample or str
        """
        return self.input_samples.get(sample_name, sample_name)


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
    A container class for specifications for converting one sample (the "primary
    sample") into another. Mostly handled by inheriting classes.
    """
    def __init__(self, plan_step, transformation):
        self.plan_step = plan_step
        self.plan = self.plan_step.plan


class Leg:
    """
    Aclass describing frequently-used chain of OperationTypes that converts one
    sample into another (the "primary samples"). Generally does not allow any
    branching of the primary samples.
    """
    # The oder of OperationTypes
    leg_order = []

    # The list of I/O names that identify the primary sample
    primary_handles = []

    def __init__(self, plan_step, cursor):
        """
        :param plan_step: the PlanStep containing this Leg
        :type plan_step: PlanStep
        :param cursor: the Cursor
        :type cursor: Cursor
        """
        self.plan_step = plan_step
        self.ext_plan = self.plan_step.plan
        self.aq_plan = self.ext_plan.aq_plan
        self.session = self.ext_plan.session
        self.cursor = cursor

        self.op_data, self.wires = self.create_operations()

        # This is no longer a good name for this variable.
        self.sample_io = {}

    # Does it make sense to populate this intermediate object?
    # Why not just build the array of operations?
    def create_operations(self):
        """
        Instantiates operations and places them in a list along with data for
        populating ContainerType fields. Also wires the operations together
        based on primary sample. Returns the list of operation data and the list
        of Wires

        :return: list
        """

        op_data = []
        wires = []

        for ot_attr in self.leg_order:
            if isinstance(ot_attr, dict):
                ot_name = ot_attr["name"]
            else:
                ot_name = ot_attr

            od = copy.deepcopy(get_obj_by_name(self.ext_plan.defaults, ot_name))
            od = od or { "defaults": {} }
            od["operation"] = self.initialize_op(ot_attr)
            od["name"] = od["operation"].operation_type.name
            od["container_types"] = self.get_container_types(od["name"])
            op_data.append(od)

            # Maybe this should happen in a different method?
            # Could make more sense in Leg.add()
            if len(op_data) > 1:
                wire = self.get_wire_pair(op_data[-2]["operation"], od["operation"])
                if not None in wire:
                    wires.append(wire)

            self.cursor.decr_y()

        return [op_data, wires]

    def initialize_op(self, ot_name):

        if isinstance(ot_name, str):
            ot_attr = {"name": ot_name}
        elif isinstance(ot_name, dict):
            ot_attr = ot_name

        ot_attr["deployed"] = True
        op_types = self.session.OperationType.where(ot_attr)

        if len(op_types) != 1:
            msg = "Didn't find a unique Operation Type for %s: %s"
            ots = [ot.category + " > " + ot.name for ot in op_types]
            print(msg % (ot_attr["name"], ots))

        op_type = op_types[0]
        op = op_type.instance()
        op.x = self.cursor.x
        op.y = self.cursor.y

        return op

    def get_container_types(self, ot_name):
        """
        Returns the container types data for a specific OperationType.

        :param ot_name: the name of the OperationType
        :type ot_name: str
        :return: dict
        """
        default_container_types = self.ext_plan.aq_defaults["container_types"]
        ct = copy.deepcopy(get_obj_by_name(default_container_types, ot_name))

        if ct:
            ct.pop("name")
        else:
            ct = {}

        return ct

    def get_container(self, ot_name, io_name, role, container_opt=None):
        """
        Gets a container (ObjectType) for an input or output.

        :param ot_name: the name of the OperationType
        :type ot_name: str
        :param io_name: the name ("handle") of the input or output
        :type io_name: str
        :param role: the role ("input" or "output")
        :type role: str
        :param container_opt: an option for specifying one of several containers
        :type container_opt: str
        :return: ObjectType
        """
        ctypes = get_obj_by_name(self.op_data, ot_name)["container_types"].get(io_name)

        if ctypes:
            container_name = ctypes[role + "_container_type"]

            if isinstance(container_name, dict):
                if container_opt:
                    container_name = container_name[container_opt]

                else:
                    raise Exception("Option required to specify container: " + container_name)

            return self.session.ObjectType.where({"name": container_name})[0]

    # Is there any reason why this can't be done as the operations
    # are being created?
    def add(self, container_opt=None):
        """
        Sets the input and output for the list of Operations, then adds the
        operations and wires to the Aq Plan object.

        :param container_opt: an option for specifying one of several containers
        :type container_opt: str
        """
        self.set_io(container_opt)
        self.aq_plan.add_operations([od["operation"] for od in self.op_data])
        self.aq_plan.add_wires(self.wires)
        print("### " + str(len(self.aq_plan.operations)) + " total operations")
        print()

    def set_io(self, container_opt):
        """
        Sets the input and output for the list of Operations. Propagates the
        primary sample forward through the chain.

        :param container_opt: an option for specifying one of several containers
        :type container_opt: str
        """
        for i in range(len(self.op_data)):
            od = self.op_data[i]
            op = od["operation"]

            step_defaults = od["defaults"]
            this_io = { **step_defaults, **self.sample_io }

            for ft in op.operation_type.field_types:
                io_object = this_io.get(ft.name)

                is_sample = isinstance(io_object, Sample)
                is_item = isinstance(io_object, Item)
                is_array = isinstance(io_object, list)

                if is_sample or is_array:
                    container = self.get_container(op.operation_type.name, ft.name, ft.role, container_opt)
                    if is_sample:
                        try:
                            op.set_field_value(ft.name, ft.role, sample=io_object, container=container)
                        except AquariumModelError as e:
                            print("%s: %s" % (od["name"], e))

                    else:
                        values = [{
                            "sample": io_object.pop(0),
                            "container": container
                        }]

                        try:
                            op.set_field_value_array(ft.name, ft.role, values)
                        except AquariumModelError as e:
                            print("%s: %s" % (od["name"], e))

                        for obj in io_object:
                            try:
                                op.add_to_field_value_array(ft.name, ft.role, sample=obj, container=container)
                            except AquariumModelError as e:
                                print("%s: %s" % (od["name"], e))

                elif is_item:
                    try:
                        op.set_field_value(ft.name, ft.role, item=io_object)
                    except AquariumModelError as e:
                        print("%s: %s" % (od["name"], e))

                else:
                    try:
                        op.set_field_value(ft.name, ft.role, value=io_object)
                    except AquariumModelError as e:
                        print("%s: %s" % (od["name"], e))

            # what if i == 0?
            self.propagate_sample(self.op_data[i - 1]["operation"], self.op_data[i]["operation"])

            print("Set IO for " + od["name"])

    def wire_ops(self, upstr_op, dnstr_op):
        """
        Wires two operations together based on primary sample.
        Propagates the sample from the upstream op to the downstream op.

        :param upstr_op: the upstream (earlier) Operation
        :type upstr_op: Operation
        :param dnstr_op: the downstream (later) Operation
        :type dnstr_op: Operation
        """
        wire_pair = self.get_wire_pair(upstr_op, dnstr_op)
        self.aq_plan.add_wires([wire_pair])
        self.propagate_sample(upstr_op, dnstr_op)

    def wire_input_array(self, upstr_ops, dnstr_op):
        """
        Takes a list of upstream Operations and wires them to an array input
        of a downstream Operation.

        :param upstr_ops: list of upstream (earlier) Operations
        :type upstr_ops: list
        :param dnstr_op: the downstream (later) Operation
        :type dnstr_op: Operation
        """
        dnstr_fvs = self.primary_io_array(dnstr_op, "input")

        for upstr_op in upstr_ops:
            w0 = self.primary_io(upstr_op, "output")
            w1 = [fv for fv in dnstr_fvs if fv.sample.name == w0.sample.name][0]
            wire_pair = [w0, w1]
            self.aq_plan.add_wires([wire_pair])

    # This method may be redundant
    def propagate_sample(self, upstr_op, dnstr_op):
        """
        Gets the output Sample for the upstream Operation and sets the
        primary input for the downstream Operation to have the same Sample.

        :param upstr_op: the upstream (earlier) Operation
        :type upstr_ops: Operation
        :param dnstr_op: the downstream (later) Operation
        :type dnstr_op: Operation
        """
        upstr_sample = None

        for h in self.primary_handles:
            try:
                fv = upstr_op.input(h)
            except:
                fv = None

            if fv:
                upstr_sample = fv.sample

        if upstr_sample:
            for h in self.primary_handles:
                fv = dnstr_op.input(h)
                if fv:
                    # TODO: don't override samples that are already set
                    try:
                        fv.set_value(sample=upstr_sample)
                    except AquariumModelError as e:
                        print("%s: %s" % (dnstr_op.operation_type.name, e))

    def get_wire_pair(self, upstr_op, dnstr_op):
        """
        Gets a pair of FieldValues correspondint to the primary input and output
        of the downstream and upstream Operations, respectively.

        :param upstr_op: the upstream (earlier) Operation
        :type upstr_ops: Operation
        :param dnstr_op: the downstream (later) Operation
        :type dnstr_op: Operation
        :return: list
        """
        w0 = self.primary_io(upstr_op, "output")
        w1 = self.primary_io(dnstr_op, "input")
        return [w0, w1]

    def primary_io(self, op, role):
        """
        Gets the primary input or output FieldValue for an Operation.

        :param op: the Operation
        :type op: Operation
        :param role: the role of the FieldValue
        :type role: str
        :return: FieldValue
        """
        fvs = self.primary_io_array(op, role)
        if fvs: return fvs[0]

    def primary_io_array(self, op, role):
        """
        Gets the list of primary input or output FieldValues for an Operation.

        :param op: the Operation
        :type op: Operation
        :param role: the role of the FieldValues
        :type role: str
        :return: list
        """
        return [fv for fv in op.field_values if fv.role == role and fv.name in self.primary_handles]

    def select_op(self, ot_name):
        """
        Returns the operation of a given OperationType from the op_data attribute.

        :param ot_name: the name of the OperationType of the Operation to return
        :type ot_name: str
        :return: Operation
        """
        if isinstance(ot_name, dict):
            ot_name = ot_name["name"]

        selected = [od for od in self.op_data if od["name"] == ot_name]
        if selected: return selected[0]["operation"]

    def get_output_op(self):
        """Gets the last Operation in the leg_order."""
        return self.get_op_by_index(-1)

    def get_input_op(self):
        """Gets the first Operation in the leg_order."""
        return self.get_op_by_index(0)

    def get_op_by_index(self, i):
        """Returns an Operation from the leg_order based on index."""
        if self.leg_order:
            ot_attr = self.leg_order[i]

            if isinstance(ot_attr, dict):
                ot_name = ot_attr["name"]
            else:
                ot_name = ot_attr

            return self.select_op(ot_name)

    def set_start_date(self, start_date):
        """
        Sets a start date for the Leg.

        :param start_date: the date to move the Operation into "pending."
        :type start_date: Date
        """
        op = self.get_input_op()
        v = "{ \"delay_until\": \"%s\" }" % start_date
        op.set_field_value("Options", "input", value=v)

    @classmethod
    def length(cls):
        """Returns the number of Operations in the Leg."""
        return len(cls.leg_order)

# TODO: Fix this so that it can deal with fractional increments.
class Cursor:
    """A class to keep track of where to put the next operation."""
    def __init__(self, x=None, y=None):
        x = x or 1
        y = y or 10

        self.x_incr = 192
        self.y_incr = 64

        self.set_x(x, update=False)
        self.set_y(y, update=False)

        self.x_home = self.x
        self.max_x = self.x
        self.min_x = self.x

        self.y_home = self.y
        self.max_y = self.y
        self.min_y = self.y

    def set_x(self, x, update=True):
        self.x = round(x * self.x_incr)
        if update: self.update_max_min_x()

    def set_y(self, y, update=True):
        self.y = round(y * self.y_incr)
        if update: self.update_max_min_y()

    def set_xy(self, x, y, update=True):
        self.set_x(x, update)
        self.set_y(y, update)
        if update: self.update_max_min()

    def incr_x(self, mult=1):
        self.x += round(mult * self.x_incr)
        self.update_max_x()
        # print("x = %d" % self.x)

    def decr_x(self, mult=1):
        self.x -= round(mult * self.x_incr)
        self.update_min_x()
        # print("x = %d" % self.x)

    def incr_y(self, mult=1):
        self.y += round(mult * self.y_incr)
        self.update_max_y()
        # print("y = %d" % self.y)

    def decr_y(self, mult=1):
        self.y -= round(mult * self.y_incr)
        self.update_min_y()
        # print("y = %d" % self.y)

    def set_x_home(self, x=None):
        if x:
            self.x_home = round(x * self.x_incr)
        else:
            self.x_home = self.x

    def return_x(self):
        self.x = self.x_home

    def set_y_home(self, y=None):
        if y:
            self.y_home = round(y * self.y_incr)
        else:
            self.y_home = self.y

    def return_y(self):
        self.y = self.y_home

    def set_home(self):
        self.set_x_home()
        self.set_y_home()

    def return_xy(self):
        self.return_x()
        self.return_y()

    def update_max_x(self):
        if self.x > self.max_x:
            self.max_x = self.x

    def update_min_x(self):
        if self.x < self.min_x:
            self.min_x = self.x

    def update_max_y(self):
        if self.y > self.max_y:
            self.max_y = self.y

    def update_min_y(self):
        if self.y < self.min_y:
            self.min_y = self.y

    def update_max_min_x(self):
        self.update_max_x()
        self.update_min_x()

    def update_max_min_y(self):
        self.update_max_y()
        self.update_min_y()

    def update_max_min(self):
        self.update_max_min_x()
        self.update_max_min_y()

    def get_xy(self):
        return [self.x, self.y]

    def advance_to_next_step(self):
        self.set_xy(round(self.min_x / self.x_incr), round(self.min_y / self.y_incr))
        self.decr_y()
        self.set_home()
