import sys
from datetime import datetime, timedelta
from pympler import tracker

trident_path = '/Users/devin/work/trident'
sys.path.append(trident_path)
ext_plan_path = '/Users/devin/work/ext-plan-pydent'
sys.path.append(ext_plan_path)

from aq_classes import Cursor, Leg
from xplan.xplans import XPlan
from prot_stab_legs import OvernightLeg, NaiveLeg, InductionLeg, SortLeg, FlowLeg, ProtStabLeg

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

while True:
    print("Enter the day you want to start the experiment.")
    print("The date must be on a Friday.")
    print("If you don't enter anything, the plan will be scheduled as soon as possible.")
    today = input("Start date (MM/DD/YY): ")

    if not today:
        today = datetime.today()
        break

    today = datetime.strptime(today, '%m/%d/%y')
    if today.weekday() == 4:
        break

    else:
        print()
        print("You entered a value that is not on a Friday. Try again.")

dow = today.weekday()

if dow <= 4:
    delay = timedelta(days=(4 - dow))
else:
    delay = timedelta(days=(11 - dow))

start_date = today + delay

print("\nPlanning experiment to start on " + start_date.strftime('%m/%d/%y'))
print()

for step_id in plan.step_ids(plan.protstab_round_steps()):
    plan_step = plan.step(step_id)

    if int(step_id) > 1:
        prev_plan_step = plan.step(step_id - 1)
        prev_step_outputs = prev_plan_step.output_operations
    else:
        prev_step_outputs = {}

    new_inputs = {}

    for input_yeast in plan_step.yeast_inputs():
        st_name = plan.input_samples[input_yeast].sample_type.name
        is_library = st_name == 'DNA Library'

        if not prev_step_outputs.get(input_yeast):
            cursor.incr_y(2)
            container_opt = 'library start' if is_library else 'control'
            overnight_leg = OvernightLeg(plan_step, cursor, aq_defaults_path)
            overnight_leg.set_yeast(input_yeast)
            overnight_leg.add(container_opt)
            overnight_leg.set_start_date(start_date.date())
            print("Planning innoculation of %s on %s" % (input_yeast, str(start_date.date())))
            cursor.return_y()

            if input_yeast in plan.ngs_samples:
                cursor.decr_y(SortLeg.length() - NaiveLeg.length())
                naive_leg = NaiveLeg(plan_step, cursor, aq_defaults_path)
                naive_leg.set_yeast(input_yeast)
                naive_leg.add('library')
                cursor.return_y()

                upstr_op = overnight_leg.select_op('Innoculate Yeast Library')
                dnstr_op = naive_leg.select_op('Store Yeast Library Sample')
                naive_leg.wire_to_prev(upstr_op, dnstr_op)

            new_inputs[input_yeast] = overnight_leg.get_innoculate_op()

        upstr_op = prev_step_outputs.get(input_yeast) or new_inputs.get(input_yeast)
        input_sample = upstr_op.output('Yeast Culture').sample

        cursor.set_x(upstr_op.x)

        if int(step_id) > 1 and is_library:
            cursor.decr_x(2)
        else:
            cursor.incr_x()

        cursor.return_y()

        cursor.incr_y(2)
        container_opt = 'library' if is_library else 'control'
        induction_leg = InductionLeg(plan_step, cursor, aq_defaults_path)
        induction_leg.set_yeast(input_yeast)
        induction_leg.add(container_opt)
        cursor.return_y()

        dnstr_op = induction_leg.select_op('Dilute Yeast Library')
        induction_leg.wire_to_prev(upstr_op, dnstr_op)

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
                    ngs_sample = dst['sample'] in plan.ngs_samples
                    if ngs_sample:
                        this_leg = SortLeg(plan_step, cursor, aq_defaults_path)
                    else:
                        this_leg = FlowLeg(plan_step, cursor, aq_defaults_path)

                    this_leg.set_yeast(input_yeast)
                    this_leg.set_protease(src)
                    # this_leg.set_uri(src, dst)

                    # This is not a good way to set these variables
                    if ngs_sample:
                        this_leg.sample_io['Control?'] = 'no'
                    else:
                        yeast_name = this_leg.sample_io['Labeled Yeast Library'].name
                        if yeast_name == 'EBY100 + pETcon3':
                            this_leg.sample_io['Control?'] = 'autofluorescence'
                        elif yeast_name == 'AMA1-best':
                            if this_leg.sample_io['Protease Concentration'] == 0:
                                this_leg.sample_io['Control?'] = 'high-fitc'
                            else:
                                this_leg.sample_io['Control?'] = 'protease'

                    this_leg.add(container_opt)

                    upstr_op = induction_leg.select_op('Dilute Yeast Library')
                    dnstr_op = this_leg.select_op('Challenge and Label')
                    this_leg.wire_to_prev(upstr_op, dnstr_op)

                    data_assoc = { 'destination': dst['sample'] }
                    plan.update_temp_data_assoc(dnstr_op, data_assoc)

                    output_op = this_leg.get_innoculate_op()

                    if output_op:
                        plan_step.add_output_operation(dst['sample'], output_op)
                        plan.add_input_sample(dst['sample'], output_op.output('Yeast Culture').sample)

                    cursor.incr_x()
                    cursor.return_y()

            cursor.incr_x()

    cursor.update_max_x()
    # cursor.return_x()
    cursor.decr_y(SortLeg.length() + 3)
    cursor.set_y_home()

    if start_date.weekday() == 4:
        incr = 3
    else:
        incr = 2

    start_date += timedelta(days=incr)

    print(plan_step.name + ' complete')
    print()

plan.launch_aq_plan()
plan.add_data_associations()

url = plan.aq_plan.session.url + "/plans?plan_id={}".format(plan.aq_plan.id)
print("Created Plan: {}".format(url))
print("{} total operations.".format(len(plan.aq_plan.operations)))
print("{} total wires.".format(len(plan.aq_plan.wires)))

test_plan(plan, out_path, ref_path)

print("Test passed!")
delete = input("Do you want to delete this plan? (y/n) ")
if delete == 'y' or delete == 'Y':
    plan.aq_plan.delete()
