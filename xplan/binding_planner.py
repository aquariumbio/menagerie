import sys
import os
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

ext_plan_path = '/Users/devin/Documents/work/ext-plan-pydent'
sys.path.append(ext_plan_path)

from plans import Cursor, Leg
from xplan.xplans import XPlan

from prot_stab_legs import SortLeg

from plan_tests import test_plan
from user_input import get_input

inputs = get_input()

start_date = inputs['start_date']
plan = XPlan(inputs['aq_plan_name'], inputs['aq_instance'])

cursor = Cursor(y=18)

for step_id in plan.step_ids(plan.get_steps_by_type('protstab_round')):
    plan_step = plan.step(step_id)
    plan_step.create_step(cursor, start_date)

    cursor.update_max_x()
    cursor.decr_y(SortLeg.length() + 3)
    cursor.set_y_home()

    if start_date.weekday() == 4:
        incr = 3
    else:
        incr = 2

    start_date += timedelta(days=incr)

    print(plan_step.name + ' complete')
    print()

plan.create_aq_plan()
plan.add_data_associations()

url = plan.aq_plan.session.url + "/plans?plan_id={}".format(plan.aq_plan.id)
print("Created Plan: {}".format(url))
print("{} total operations.".format(len(plan.aq_plan.operations)))
print("{} total wires.".format(len(plan.aq_plan.wires)))

# out_path = os.path.join(plan.plan_path, 'dump.json')
# ref_path = os.path.join(plan.plan_path, 'dump-ref.json')
# test_plan(plan, out_path, ref_path)
# print("Test passed!")

delete = input("Do you want to delete this plan? (y/n) ")
if delete == 'y' or delete == 'Y':
    plan.aq_plan.delete()
