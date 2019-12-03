import sys
import os
import time
import warnings
# warnings.filterwarnings('ignore')

from util.plans import Cursor
from util.cloning_plans import CloningPlan
from util.plasmid_assembly_legs import GibsonLeg, SangerSeqLeg, PCRLeg
from util.plasmid_assembly_legs import YeastTransformationLeg, YeastGenotypingLeg

from util.plan_tests import test_plan
from util.user_input import get_input

# inputs = get_input(start_date=False)
inputs = {
    'plan_path': 'cloning_plans/test_gibson',
    'aq_instance': 'laptop'
}

plan = CloningPlan(inputs['plan_path'], inputs['aq_instance'])

cursor = Cursor(y=26)

plan_step = plan.get_steps_by_type("pcr")[0]
step_outputs = plan_step.create_step(cursor)
cursor.advance_to_next_step()

plan_step = plan.get_steps_by_type("gibson")[0]
step_outputs = plan_step.create_step(cursor, n_qcs=2, step_outputs=step_outputs)
cursor.advance_to_next_step()

plan.create_aq_plan()

url = plan.aq_plan.session.url + "/plans?plan_id={}".format(plan.aq_plan.id)
print("Created Plan: {}".format(url))
print("{} total operations.".format(len(plan.aq_plan.operations)))
print("{} total wires.".format(len(plan.aq_plan.wires)))

# cost = pplan.aq_plan.estimate_cost()

# Paths for regression testing the output plan against a reference.
# out_path = os.path.join(plan_test_path, 'plan.json')
# ref_path = os.path.join(plan_test_path, 'plan-ref.json')

# test_plan(plan, out_path, ref_path)