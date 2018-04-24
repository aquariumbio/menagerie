import json
import copy

import pydent
from pydent import models
from pydent.models import Sample

def get_op(leg, name):
    ops = [x for x in leg if x['name'] == name]
    if ops: return ops[0]


class Leg:

    leg_order = []
    primary_handles = []

    def __init__(self, plan_step, cursor, aq_defaults_path):
        self.plan_step = plan_step
        self.ext_plan = self.plan_step.plan
        self.aq_plan = self.ext_plan.aq_plan
        self.session = self.ext_plan.session
        self.cursor = cursor
        self.set_params()
        self.set_container_types(aq_defaults_path)

        self.sample_io = {}
        self.aq_plan_objs = Leg.get_init_plan_objects()

    def get_init_plan_objects():
        init_plan_objs = {
            'ops': [],
            'wires': []
        }
        return init_plan_objs

    def set_params(self):
        self.params = []
        for x in self.leg_order:
            p = copy.deepcopy(get_op(self.ext_plan.defaults, x))
            p = p or { "name": x, "defaults": {} }
            self.params.append(p)

    def set_container_types(self, aq_defaults_path):
        with open(aq_defaults_path, 'r') as f:
            aq_defaults = json.load(f)
            default_container_types = aq_defaults['container_types']

        self.container_types = []
        for param in self.params:
            name = param['name']
            p = copy.deepcopy(get_op(default_container_types, name))
            p = p or { "name": name, "defaults": {} }
            self.container_types.append(p)

    def get_container(self, op_name, io_name, role, container_opt=None):
        ctypes = get_op(self.container_types, op_name).get(io_name)

        if ctypes:
            container_name = ctypes[role + '_container_type']

            if isinstance(container_name, dict):
                if container_opt:
                    container_name = container_name[container_opt]

                else:
                    raise 'Option required to specify container: ' + container_name
                    
            return self.session.ObjectType.where({'name': container_name})[0]

    def add(self, source, destination, container_opt=None):
        self.create(source, destination, container_opt)
        self.aq_plan.add_operations(self.aq_plan_objs['ops'])
        self.aq_plan.add_wires(self.aq_plan_objs['wires'])
        print('### ' + str(len(self.aq_plan.operations)) + ' total operations')
        print()
        return self.aq_plan_objs

    def create(self, source, destination, container_opt):
        for i in range(len(self.params)):
            step_params = self.params[i]
            print("Added " + step_params['name'])
            op = self.initialize_op(step_params['name'])

            step_defaults = step_params['defaults']
            this_io = { **step_defaults, **self.sample_io }

            for ft in op.operation_type.field_types:
                io_object = this_io.get(ft.name)

                is_sample = isinstance(io_object, Sample)
                is_array = isinstance(io_object, list)

                if is_sample or is_array:
                    container = self.get_container(op.operation_type.name, ft.name, ft.role, container_opt)
                    if is_sample:
                        op.set_field_value(ft.name, ft.role, sample=io_object, container=container)

                    else:
                        values = [{
                            'sample': io_object.pop(0),
                            'container': container
                        }]
                        op.set_field_value_array(ft.name, ft.role, values)

                        for obj in io_object:
                            op.add_to_field_value_array(ft.name, ft.role, sample=obj, container=container)

                else:
                    op.set_field_value(ft.name, ft.role, value=io_object)

            self.aq_plan_objs['ops'].append(op)

            if i > 0: self.wire_internal(i)

            self.cursor.decr_y()

    def initialize_op(self, ot_name):
        op_types = self.session.OperationType.where({
            'name': ot_name,
            "deployed": True
        })
        op_type = op_types[0]

        op = op_type.instance()
        op.x = self.cursor.x
        op.y = self.cursor.y

        return op

    def wire_internal(self, i):
        upstr_op = self.aq_plan_objs['ops'][i - 1]
        dnstr_op = self.aq_plan_objs['ops'][i]
        wire = self.get_wire_pair(upstr_op, dnstr_op)
        self.aq_plan_objs['wires'].append(wire)
        self.propagate_sample(upstr_op, dnstr_op)

    # This method may be redundant
    def propagate_sample(self, upstr_op, dnstr_op):
        upstr_sample = None

        for h in self.primary_handles:
            fv = upstr_op.input(h)
            if fv:
                upstr_sample = fv.sample

        if upstr_sample:
            for h in self.primary_handles:
                fv = dnstr_op.input(h)
                if fv:
                    # TODO: don't override samples that are already set
                    fv.set_value(sample=upstr_sample)

    def get_wire_pair(self, upstr_op, dnstr_op):
        w0 = self.primary_io(upstr_op, 'output')
        w1 = self.primary_io(dnstr_op, 'input')
        return [w0, w1]

    def primary_io(self, op, role):
        return next(fv for fv in op.field_values if fv.role == role and fv.name in self.primary_handles)



class Cursor:
    def __init__(self, x=None, y=None):
        self.x = x or 64
        self.x_incr = 192

        self.y = y or 1536
        self.y_incr = 64

        self.x_home = self.x
        self.max_x = self.x

        self.y_home = self.y
        self.max_y = self.y

    def set_x(self, x):
        self.x = x

    def set_y(self, y):
        self.y = y

    def set_xy(self, x, y):
        self.set_x(x)
        self.set_y(y)

    def incr_x(self, mult=1):
        self.x += mult * self.x_incr

    def decr_x(self, mult=1):
        self.x -= mult * self.x_incr

    def incr_y(self, mult=1):
        self.y += mult * self.y_incr

    def decr_y(self, mult=1):
        self.y -= mult * self.y_incr

    def set_x_home(self, x=None):
        self.x_home = x or self.x

    def return_x(self):
        self.x = self.x_home

    def set_y_home(self, y=None):
        self.y_home = y or self.y

    def return_y(self):
        self.y = self.y_home

    def update_max_x(self):
        if self.x > self.max_x:
            self.max_x = self.x

    def get_xy(self):
        return [self.x, self.y]
