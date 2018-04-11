import sys
trident_path = '/Users/devin/work/trident'
sys.path.append(trident_path)
ext_plan_path = '/Users/devin/work/ext-plan-pydent'
sys.path.append(ext_plan_path)

from aq_classes import Cursor
from pup_plan.pup_plans import PupPlan
from golden_gate_leg import GoldenGateLeg

import os

from plan_tests import test_plan

import warnings
warnings.filterwarnings('ignore')

# Path for login credentials and whatnot.
config_path = os.path.join(ext_plan_path, 'config.yml')

# Paths for input configurations.
plan_test_path = os.path.join(ext_plan_path, 'pup_plan/golden_gate_test')
path_stub = os.path.join(plan_test_path, 'config')
plan_path = os.path.join(path_stub, 'request-aq.json')
aq_defaults_path = os.path.join(path_stub, 'golden_gate_aquarium_defaults.json')
plan_defaults_path = os.path.join(path_stub, 'golden_gate_plan_defaults.json')

# Paths for regression testing the output plan against a reference.
out_path = os.path.join(plan_test_path, 'plan.json')
ref_path = os.path.join(plan_test_path, 'plan-ref.json')

aq_plan_name = "Puppeteer Test Plan"
plan = PupPlan(aq_plan_name, plan_path, plan_defaults_path, config_path)

assembly_leg_order = [
    'Assemble NEB Golden Gate',
    'Transform Cells from Stripwell',
    'Plate Transformed Cells',
    'Check Plate',
    'Make Overnight Suspension',
    'Make Miniprep',
    'Send to Sequencing',
    'Upload Sequencing Results'
]

cursor = Cursor()

for step_id in plan.step_ids():
    plan_step = plan.step(step_id)

    txns = plan_step.transformations
    for txn in txns:
        src = txn['source']
        for dst in txn['destination']:
            this_leg = GoldenGateLeg(plan_step, src, dst, assembly_leg_order, aq_defaults_path)
            aq_plan_objs = this_leg.add(cursor)

# cost = pplan.aq_plan.estimate_cost()

test_plan(plan, out_path, ref_path)
