import sys
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
plan_path = os.path.join(path_stub, 'generated_protstab_with_old_stubs.json')
aq_defaults_path = os.path.join(path_stub, 'protstab_aquarium_defaults.json')
plan_defaults_path = os.path.join(path_stub, 'protstab_plan_defaults_nursery.json')

# Paths for regression testing the output plan against a reference.
out_path = os.path.join(plan_test_path, 'plan.json')
ref_path = os.path.join(plan_test_path, 'plan-ref.json')

aq_plan_name = "ProtStab Test Plan 2"
plan = XPlan(aq_plan_name, plan_path, plan_defaults_path, config_path)

# Specify the order of opertions in each type of leg.
# This should probably go somewhere else.

# overnight_leg_order = (
#     'Innoculate Yeast Library',
#     'Dilute Yeast Library'
# )
overnight_leg_order = ['Innoculate Yeast Library']

def add_overnight_leg(plan_step, cursor):
    overnight_leg = OvernightLeg(plan_step, None, None, overnight_leg_order, aq_defaults_path)
    overnight_plan_objs = overnight_leg.add(cursor, 'library start')
    cursor.decr_y()
    cursor.set_x_home(cursor.x_home + 2 * cursor.x_incr)
    return overnight_leg

naive_leg_order = ['Store Yeast Library Sample']

induction_leg_order = ['Dilute Yeast Library']

sample_leg_order = (
    'Challenge and Label',
    'Sort Yeast Display Library',
    'Innoculate Yeast Library',
    'Store Yeast Library Sample'
)

ngs_leg_order = (
    'Innoculate Yeast Library',
    'Store Yeast Library Sample'
)

# This keeps track of where to put the next operation in the GUI.
cursor = Cursor()

prev_step_outputs = {}

for step_id in plan.step_ids(plan.protstab_round_steps()):
    plan_step = plan.step(step_id)
    print(plan_step.name)

    if not prev_step_outputs:
        # This should only happen on the first protstab round
        overnight_leg = add_overnight_leg(plan_step, cursor)
        samples = plan.input_samples.items()

        # Can only handle one library
        dst = next(k for k, v in samples if v.sample_type.name == "DNA Library")
        next_step_inputs = { dst: overnight_leg.get_output_op() }

    else:
        cursor.decr_y(len(sample_leg_order))
        next_step_inputs = prev_step_outputs

    yeast_inputs = sorted(next_step_inputs.keys(), key=lambda k: next_step_inputs[k].x)

    for input_yeast in yeast_inputs:
        upstr_op = next_step_inputs[input_yeast]
        input_sample = upstr_op.output('Yeast Culture').sample

        induction_leg = InductionLeg(plan_step, None, None, induction_leg_order, aq_defaults_path)
        overnight_plan_objs = induction_leg.add(cursor, 'library')

        dnstr_op = ProtStabLeg.select_op(overnight_plan_objs['ops'], 'Dilute Yeast Library')
        induction_leg.wire_to_prev(upstr_op, dnstr_op)

        cursor.decr_y()

        txns = [t for t in plan_step.transformations if input_yeast in t['source']]

        for txn in txns:
            src = txn['source']

            for destination in txn['destination']:
                tk = XPlan.get_treatment_key(destination)

                if 'negative' in tk: continue
                if 'positive' in tk: continue

                if tk == 'naive':
                    cursor.decr_y(len(sample_leg_order) - len(naive_leg_order))
                    this_leg = NaiveLeg(plan_step, src, destination, naive_leg_order, aq_defaults_path)
                    overnight_ot = 'Innoculate Yeast Library'
                    this_ot = 'Store Yeast Library Sample'
                else:
                    this_leg = SampleLeg(plan_step, src, destination, sample_leg_order, aq_defaults_path)
                    overnight_ot = 'Dilute Yeast Library'
                    this_ot = 'Challenge and Label'

                this_plan_objs = this_leg.add(cursor, 'library')

                upstr_op = ProtStabLeg.select_op(overnight_plan_objs['ops'], overnight_ot)
                dnstr_op = ProtStabLeg.select_op(this_plan_objs['ops'], this_ot)
                this_leg.wire_to_prev(upstr_op, dnstr_op)

                prev_step_outputs[destination] = this_leg.get_output_op()

                cursor.incr_x()

                cursor.incr_y(len(sample_leg_order))

            cursor.incr_x()

    cursor.update_max_x()
    cursor.return_x()
    cursor.decr_y(1)

    # elif plan_step.operator_type == 'protstab_round_2+':
    #     cursor.decr_y(len(sample_leg_order))
    #     next_step_inputs = {}
    #
    #     for i in plan_step.uniq_plan_inputs():
    #         if i in prev_step_outputs.keys():
    #             if prev_step_outputs[i]:
    #                 next_step_inputs[i] = prev_step_outputs[i]
    #
    #     prev_step_outputs = {}
    #
    #     # Need to enforce an order based on the x position
    #     yeast_inputs = sorted(next_step_inputs.keys(), key=lambda k: next_step_inputs[k].x)
    #
    #     for input_yeast in yeast_inputs:
    #         upstr_op = next_step_inputs[input_yeast]
    #         input_sample = upstr_op.output('Yeast Culture').sample
    #
    #         induction_leg = InductionLeg(plan_step, None, None, induction_leg_order, aq_defaults_path)
    #         overnight_plan_objs = induction_leg.add(cursor, 'library')
    #
    #         dnstr_op = ProtStabLeg.select_op(overnight_plan_objs['ops'], 'Dilute Yeast Library')
    #         induction_leg.wire_to_prev(upstr_op, dnstr_op)
    #
    #         cursor.decr_y()
    #
    #         txn = [t for t in plan_step.transformations if input_yeast in t['source']][0]
    #         src = txn['source']
    #         for destination in txn['destination']:
    #             tk = XPlan.get_treatment_key(destination)
    #
    #             if 'negative' in tk: continue
    #             if 'positive' in tk: continue
    #
    #             this_leg = SampleLeg(plan_step, src, destination, sample_leg_order, aq_defaults_path)
    #
    #             this_plan_objs = this_leg.add(cursor, 'library')
    #
    #             upstr_op = ProtStabLeg.select_op(overnight_plan_objs['ops'], 'Dilute Yeast Library')
    #             dnstr_op = ProtStabLeg.select_op(this_plan_objs['ops'], 'Challenge and Label')
    #             this_leg.wire_to_prev(upstr_op, dnstr_op)
    #
    #             prev_step_outputs[destination] = this_leg.get_output_op()
    #
    #             cursor.incr_x()
        #         cursor.incr_y(len(this_leg.aq_plan_objs['ops']))
        #
        #     cursor.incr_y(2)
        #
        # cursor.update_max_x()
        # cursor.return_x()
        # cursor.decr_y(3)

plan.launch_aq_plan()

# test_plan(plan, out_path, ref_path)
