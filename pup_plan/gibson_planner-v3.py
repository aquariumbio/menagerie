import sys
import warnings
warnings.filterwarnings('ignore')
import time

ext_plan_path = '/Users/devin/Documents/work/ext-plan-pydent'
sys.path.append(ext_plan_path)

from aq_classes import Cursor
from pup_plan.pup_plans import PupPlan
from plasmid_assembly_legs import GibsonLeg, SangerSeqLeg, PCRLeg
from plasmid_assembly_legs import YeastTransformationLeg, YeastGenotypingLeg

import os

from plan_tests import test_plan
from user_input import get_input

start_time = time.time()

inputs = {
    "aq_plan_name": "gibson_test",
    "aq_instance": "laptop"
}
# inputs = get_input(start_date=False)

plan = PupPlan(inputs['aq_plan_name'], inputs['aq_instance'])

cursor = Cursor(x=64, y=1664)

plan_step = plan.step_by_build_method("PCR")
step_outputs = plan_step.create_step(cursor)
cursor.advance_to_next_step()

plan_step = plan.step_by_build_method("Gibson Assembly")
step_outputs = plan_step.create_step(cursor, n_qcs=3, step_outputs=step_outputs)
cursor.advance_to_next_step()

plan_step = plan.step_by_build_method("Yeast Transformation")
step_outputs = plan_step.create_step(cursor, n_qcs=3, step_outputs=step_outputs)

plan.launch_aq_plan()

# url = plan.aq_plan.session.url + "/plans?plan_id={}".format(plan.aq_plan.id)
# print("Created Plan: {}".format(url))
# print("{} total operations.".format(len(plan.aq_plan.operations)))
# print("{} total wires.".format(len(plan.aq_plan.wires)))

# cost = pplan.aq_plan.estimate_cost()

# Paths for regression testing the output plan against a reference.
# out_path = os.path.join(plan_test_path, 'plan.json')
# ref_path = os.path.join(plan_test_path, 'plan-ref.json')

# test_plan(plan, out_path, ref_path)

print(time.time() - start_time)
