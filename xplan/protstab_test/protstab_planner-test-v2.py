import sys
from datetime import datetime
from pympler import tracker

trident_path = '/Users/devin/work/trident'
sys.path.append(trident_path)
ext_plan_path = '/Users/devin/work/ext-plan-pydent'
sys.path.append(ext_plan_path)

from aq_classes import Cursor, Leg
from xplan.xplans import XPlan
from prot_stab_legs import *

import os

from plan_tests import test_plan

import warnings
warnings.filterwarnings('ignore')

# Path for login credentials and whatnot.
config_path = os.path.join(ext_plan_path, 'config.yml')

# Paths for input configurations.
plan_test_path = os.path.join(ext_plan_path, 'xplan/protstab_test')
path_stub = os.path.join(plan_test_path, 'config')
plan_path = os.path.join(path_stub, 'explicit_concentrations.json')
aq_defaults_path = os.path.join(path_stub, 'protstab_aquarium_defaults.json')
plan_defaults_path = os.path.join(path_stub, 'protstab_plan_defaults_nursery.json')

# Paths for regression testing the output plan against a reference.
out_path = os.path.join(plan_test_path, 'plan.json')
ref_path = os.path.join(plan_test_path, 'plan-ref.json')

aq_plan_name = "ProtStab Test Plan 3"
plan = XPlan(aq_plan_name, plan_path, plan_defaults_path, config_path)

# This keeps track of where to put the next operation in the GUI.
cursor = Cursor()

prev_step_outputs = {}

for step_id in plan.step_ids(plan.protstab_round_steps()):
    plan_step = plan.step(step_id)

    # if int(step_id) > 2: break

    if not prev_step_outputs:
        # This should only happen on the first protstab round
        cursor.incr_y(2)
        overnight_leg = OvernightLeg(plan_step, cursor, aq_defaults_path)
        overnight_plan_objs = overnight_leg.add(None, None, 'library start')
        cursor.return_y()

        naive_offest = SortLeg.length() - NaiveLeg.length()
        cursor.decr_y(naive_offest)
        naive_leg = NaiveLeg(plan_step, cursor, aq_defaults_path)
        naive_plan_objs = naive_leg.add(None, None, 'library')
        cursor.return_y()

        upstr_op = ProtStabLeg.select_op(overnight_plan_objs['ops'], 'Innoculate Yeast Library')
        dnstr_op = ProtStabLeg.select_op(naive_plan_objs['ops'], 'Store Yeast Library Sample')
        naive_leg.wire_to_prev(upstr_op, dnstr_op)

        # Can only handle one input library
        samples = plan.input_samples
        library_sample = next(k for k, v in samples.items() if v.sample_type.name == "DNA Library")
        next_step_inputs = { library_sample: overnight_leg.get_output_op() }

        # cursor.incr_y(naive_offest - 1)
        # cursor.set_y_home()

    else:
        next_step_inputs = { i: prev_step_outputs[i] for i in plan_step.get_inputs('DNA Library') }

        cursor.decr_y(SortLeg.length() + 2)
        cursor.set_y_home()

    yeast_inputs = sorted(next_step_inputs.keys(), key=lambda i: next_step_inputs[i].x)

    for input_yeast in yeast_inputs:
        upstr_op = next_step_inputs[input_yeast]
        input_sample = upstr_op.output('Yeast Culture').sample

        cursor.set_x(upstr_op.x)
        if int(step_id) == 1:
            cursor.incr_x()
        else:
            cursor.decr_x(2)
        cursor.return_y()

        cursor.incr_y(2)
        induction_leg = InductionLeg(plan_step, cursor, aq_defaults_path)
        induction_plan_objects = induction_leg.add( None, None, 'library')
        cursor.return_y()

        for k in Leg.get_init_plan_objects().keys():
            overnight_plan_objs[k].extend(induction_plan_objects[k])

        dnstr_op = ProtStabLeg.select_op(overnight_plan_objs['ops'], 'Dilute Yeast Library')
        induction_leg.wire_to_prev(upstr_op, dnstr_op)

        # cursor.decr_y()

        txns = [t for t in plan_step.transformations if input_yeast in t.source_samples()]

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
                    # Measured samples is not a very good descriptor here
                    # Better to have something that captures flow cytometry
                    if dst['sample'] in plan_step.measured_samples:

                        if dst['sample'] in plan.ngs_samples:
                            this_leg = SortLeg(plan_step, cursor, aq_defaults_path)

                        else:
                            this_leg = FlowLeg(plan_step, cursor, aq_defaults_path)

                        this_leg.set_protease(src)
                        overnight_ot = 'Dilute Yeast Library'
                        this_ot = 'Challenge and Label'

                    # This is supposed to deal with the naive leg but for some reason it isn't reached.
                    # else:
                        # cursor.decr_y(SortLeg.length() - NaiveLeg.length())
                        # this_leg = NaiveLeg(plan_step, cursor, aq_defaults_path)
                        # overnight_ot = 'Innoculate Yeast Library'
                        # this_ot = 'Store Yeast Library Sample'

                    this_plan_objs = this_leg.add(src, dst, 'library')

                    upstr_op = ProtStabLeg.select_op(overnight_plan_objs['ops'], overnight_ot)
                    dnstr_op = ProtStabLeg.select_op(this_plan_objs['ops'], this_ot)
                    this_leg.wire_to_prev(upstr_op, dnstr_op)

                    output_op = this_leg.get_output_op()

                    if output_op:
                        prev_step_outputs[dst['sample']] = output_op
                        plan.add_input_sample(dst['sample'], output_op.output('Yeast Culture').sample)

                    cursor.incr_x()
                    cursor.return_y()

            cursor.incr_x()

        overnight_plan_objs = Leg.get_init_plan_objects()

    cursor.update_max_x()
    # cursor.return_x()
    cursor.decr_y(1)

    print(plan_step.name + ' complete')
    print()

print(len(plan.aq_plan.operations))
print(len(plan.aq_plan.wires))
plan.launch_aq_plan()

# test_plan(plan, out_path, ref_path)
