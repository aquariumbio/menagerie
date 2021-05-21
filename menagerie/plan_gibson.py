from util.cursor import Cursor
from util.cloning_plans import CloningPlan
from util.user_input import get_input, get_args
from util.format_output import print_blue

def main():
    args = get_args()

    if args.test:
        # Override get_input() for convenience when testing code
        print_blue("RUNNING IN TEST MODE")
        inputs = {
            'plan_path': 'config/cloning/test_gibson',
            'aq_instance': 'laptop'
        }
    else:
        # Ask for inputs on the command line
        inputs = get_input(start_date=False)

    plan = CloningPlan(inputs['plan_path'], inputs['aq_instance'])

    # Keeps track of where to put the next operation in the Aquarium Designer GUI
    cursor = Cursor(y=26)

    plan_step = plan.get_steps_by_type("pcr")[0]
    step_outputs = plan_step.create_step(cursor)
    cursor.advance_to_next_step()
    plan_step.report()

    plan_step = plan.get_steps_by_type("gibson")[0]
    plan_step.create_step(cursor, n_qcs=2, step_outputs=step_outputs)
    cursor.advance_to_next_step()
    plan_step.report()

    if not args.ephemeral:
        plan.create_aq_plan()
        plan.add_data_associations()
        plan.report()

if __name__ == "__main__":
    main()