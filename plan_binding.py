from datetime import datetime, timedelta

from util.cursor import Cursor
from util.yeast_display_plans import YeastDisplayPlan
from util.user_input import get_input, get_args
from util.format_output import print_blue

def main():
    args = get_args()

    if args.test:
        # Override get_input() for convenience when testing code
        print_blue("RUNNING IN TEST MODE")
        inputs = {
            'start_date': datetime.today(),
            'plan_path': 'yeast_display_plans/test_simple_binding',
            'aq_instance': args.server
        }
    else:
        # Ask for inputs on the command line
        inputs = get_input(aq_instance=False)

    start_date = inputs['start_date']
    plan = YeastDisplayPlan(inputs['plan_path'], args.server)

    # Keeps track of where to put the next operation in the Aquarium Designer GUI
    cursor = Cursor(y=26)

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

    if not args.ephemeral:
        plan.create_aq_plan()
        plan.add_data_associations()
        plan.report()

if __name__ == "__main__":
    main()