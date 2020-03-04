from util.plans import Cursor
from util.yeast_display_plans import YeastDisplayPlan
from util.user_input import get_input, get_args
from util.format_output import print_blue

def main():
    args = get_args()
    
    if args.test:
        # Override get_input() for convenience when testing code
        print_blue("RUNNING IN TEST MODE")
        inputs = {
            'plan_path': "yeast_display_plans/test_ngs_prep_params",
            'aq_instance': "laptop"
        }
    else:
        # Ask for inputs on the command line
        inputs = get_input(start_date=False)

    plan = YeastDisplayPlan(inputs['plan_path'], inputs['aq_instance'])

    # Keeps track of where to put the next operation in the Aquarium Designer GUI
    cursor = Cursor(y=18)

    # The `plan.py` file may contain other types of steps, but we only
    #   want the `dna_seq` steps
    for plan_step in plan.get_steps_by_type('dna_seq'):
        plan_step.create_step(cursor)

        plan_step.report()

    if not args.ephemeral:
        plan.create_aq_plan()
        plan.add_data_associations()
        plan.report()

if __name__ == "__main__":
    main()