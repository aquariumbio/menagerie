import sys
import os
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

ext_plan_path = '/Users/devin/Documents/work/ext-plan-pydent'
sys.path.append(ext_plan_path)

from plans import Cursor
from xplan.xplans import XPlan

from plan_tests import test_plan
from user_input import get_input

inputs = {
    'aq_plan_name': "ngs_test",
    'aq_instance': "laptop"
}

# inputs = get_input(start_date=False)

plan = XPlan(inputs['aq_plan_name'], inputs['aq_instance'])
session = plan.session
cursor = Cursor(y=18)

for step_id in plan.step_ids(plan.get_steps_by_type('dna_seq')):
    plan_step = plan.step(step_id)
    plan_step.create_step(cursor)

    cursor.update_max_x()


plan.create_aq_plan()
# plan.add_data_associations()

# url = plan.aq_plan.session.url + "/plans?plan_id={}".format(plan.aq_plan.id)
# print("Created Plan: {}".format(url))
# print("{} total operations.".format(len(plan.aq_plan.operations)))
# print("{} total wires.".format(len(plan.aq_plan.wires)))

# # out_path = os.path.join(plan.plan_path, 'dump.json')
# # ref_path = os.path.join(plan.plan_path, 'dump-ref.json')
# # test_plan(plan, out_path, ref_path)
# # print("Test passed!")

# delete = input("Do you want to delete this plan? (y/n) ")
# if delete == 'y' or delete == 'Y':
#     plan.aq_plan.delete()
