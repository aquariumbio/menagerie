from util.cursor import Cursor
from util.cloning_plans import CloningPlan
from util.plasmid_assembly_legs import GoldenGateLeg, SangerSeqLeg

from util.user_input import get_input, get_args
from util.format_output import print_blue

def main():
    args = get_args()

    if args.test:
        # Override get_input() for convenience when testing code
        print_blue("RUNNING IN TEST MODE")
        inputs = {
            "plan_path": "golden_gate_test",
            "aq_instance": "nursery"
        }
    else:
        # Ask for inputs on the command line
        inputs = get_input(start_date=False)

    plan = CloningPlan(inputs['plan_path'], inputs['aq_instance'])

    # Keeps track of where to put the next operation in the Aquarium Designer GUI
    cursor = Cursor(y=8)

    n_seqs = 3

    for step_id in plan.step_ids():
        plan_step = plan.step(step_id)

        txns = plan_step.transformations
        for txn in txns:
            src = txn['source']
            for dst in txn['destination']:
                gg_leg = GoldenGateLeg(plan_step, cursor)
                gg_leg.set_sample_io(src, dst)
                aq_plan_objs = gg_leg.add()
                upstr_op = gg_leg.get_output_op()

                for i in range(n_seqs):
                    ss_leg = SangerSeqLeg(plan_step, cursor)
                    ss_leg.set_sample_io(src, dst)
                    aq_plan_objs = ss_leg.add()
                    dnstr_op = ss_leg.get_input_op()
                    ss_leg.wire_ops(upstr_op, dnstr_op)
                    cursor.incr_x()
                    cursor.incr_y(ss_leg.length())

                cursor.return_y()

    if not args.ephemeral:
        plan.create_aq_plan()
        plan.add_data_associations()
        plan.report()

if __name__ == "__main__":
    main()
