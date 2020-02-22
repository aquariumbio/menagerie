from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from util.plans import Cursor
from util.yeast_display_plans import YeastDisplayPlan
from util.user_input import get_input

# Ask for inputs on the command line
inputs = get_input()

# Override get_input() for convenience when testing code
# inputs = {
#     'plan_path': 'yeast_display_plans/template_stability', 
#     'start_date': datetime.today(), 
#     'aq_instance': 'laptop'
# }

start_date = inputs['start_date']
plan = YeastDisplayPlan(inputs['plan_path'], inputs['aq_instance'])

# Keeps track of where to put the next operation in the Aquarium Designer GUI
cursor = Cursor(y=18)

# The `plan.py` file may contain other types of steps, but we only
#   want the `yeast_display_round` steps
for plan_step in plan.get_steps_by_type('yeast_display_round'):
    plan_step.create_step(cursor, start_date)

    # Schedule certain operations on M, W, F
    if start_date.weekday() == 4:
        incr = 3
    else:
        incr = 2

    start_date += timedelta(days=incr)

    plan_step.report()

plan.create_aq_plan()
plan.add_data_associations()
plan.report()