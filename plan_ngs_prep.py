import sys

from util.plans import Cursor
from util.yeast_display_plans import YeastDisplayPlan
from util.user_input import get_input

# Ask for inputs on the command line
# inputs = get_input(start_date=False)

# Override get_input() for convenience when testing code
inputs = {
    'plan_path': "yeast_display_plans/template_ngs_prep_params",
    'aq_instance': "laptop"
}

plan = YeastDisplayPlan(inputs['plan_path'], inputs['aq_instance'])

# print(plan.steps[0].transformations[0].source)
# sys.exit("Terminating early")

# Keeps track of where to put the next operation in the Aquarium Designer GUI
cursor = Cursor(y=18)

# The `plan.py` file may contain other types of steps, but we only
#   want the `dna_seq` steps
for plan_step in plan.get_steps_by_type('dna_seq'):
    plan_step.create_step(cursor)

    plan_step.report()

sys.exit("Terminating early")

plan.create_aq_plan()
plan.report()