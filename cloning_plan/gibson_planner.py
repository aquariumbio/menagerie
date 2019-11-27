import sys
import warnings
warnings.filterwarnings('ignore')
import time

ext_plan_path = '/workspaces/ext-plan-pydent'
sys.path.append(ext_plan_path)

from plans import Cursor
from cloning_plan.cloning_plans import CloningPlan
from plasmid_assembly_legs import GibsonLeg, SangerSeqLeg, PCRLeg
from plasmid_assembly_legs import YeastTransformationLeg, YeastGenotypingLeg

import os

from plan_tests import test_plan
from user_input import get_input

# inputs = get_input(start_date=False)
inputs = {
    'aq_plan_name': 'json_harmonization',
    'aq_instance': 'laptop'
}

plan = CloningPlan(inputs['aq_plan_name'], inputs['aq_instance'])

cursor = Cursor(y=26)

plan_step = plan.step_by_build_method("pcr")
step_outputs = plan_step.create_step(cursor)
cursor.advance_to_next_step()

plan_step = plan.step_by_build_method("gibson")
step_outputs = plan_step.create_step(cursor, n_qcs=2, step_outputs=step_outputs)
cursor.advance_to_next_step()

# These should be moved to another script
# plan_step = plan.step_by_build_method("Yeast Transformation")
# step_outputs = plan_step.create_step(cursor, n_qcs=2, step_outputs=step_outputs)

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