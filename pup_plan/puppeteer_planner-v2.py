import sys
import warnings
warnings.filterwarnings('ignore')

ext_plan_path = '/Users/devin/Documents/work/ext-plan-pydent'
sys.path.append(ext_plan_path)

from aq_classes import Cursor
from pup_plan.pup_plans import PupPlan
from golden_gate_leg import GoldenGateLeg

import os

from plan_tests import test_plan
from user_input import get_input

inputs = {
    "aq_plan_name": "golden_gate_test",
    "aq_instance": "nursery"
}
# inputs = get_input(start_date=False)

plan = PupPlan(inputs['aq_plan_name'], inputs['aq_instance'])

cursor = Cursor(x=64, y=512)

for step_id in plan.step_ids():
    plan_step = plan.step(step_id)

    txns = plan_step.transformations
    for txn in txns:
        src = txn['source']
        for dst in txn['destination']:
            this_leg = GoldenGateLeg(plan_step, cursor)
            this_leg.set_sample_io(src, dst)
            aq_plan_objs = this_leg.add()

            cursor.incr_x()
            cursor.return_y()

plan.launch_aq_plan()
plan.add_data_associations()

url = plan.aq_plan.session.url + "/plans?plan_id={}".format(plan.aq_plan.id)
print("Created Plan: {}".format(url))
print("{} total operations.".format(len(plan.aq_plan.operations)))
print("{} total wires.".format(len(plan.aq_plan.wires)))

# cost = pplan.aq_plan.estimate_cost()

# Paths for regression testing the output plan against a reference.
# out_path = os.path.join(plan_test_path, 'plan.json')
# ref_path = os.path.join(plan_test_path, 'plan-ref.json')

# test_plan(plan, out_path, ref_path)
