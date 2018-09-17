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

n_seqs = 3
n_qcs = 3

plan_step = plan.step_by_build_method("PCR")
txns = plan_step.transformations
prev_step_outputs = {}

for txn in txns:
    src = txn['source']

    for dst in txn['destination']:
        sample_type = plan.input_samples.get(src['Template']).sample_type.name

        if sample_type == "DNA Library":
            container_opt = "dna_library"
        else:
            container_opt = "plasmid_stock"

        build_leg = PCRLeg(plan_step, cursor)
        build_leg.set_sample_io(src, dst)
        aq_plan_objs = build_leg.add(container_opt)

        prev_step_outputs[dst] = build_leg.get_output_op()
        cursor.incr_x()
        cursor.return_y()

cursor.set_xy(cursor.min_x, cursor.min_y)
cursor.decr_y()
cursor.set_home()

plan_step = plan.step_by_build_method("Gibson Assembly")
txns = plan_step.transformations

for txn in txns:
    src = txn['source']
    src["Fragment"].sort(key=lambda s: prev_step_outputs.get(s).x)

    for dst in txn['destination']:
        build_leg = GibsonLeg(plan_step, cursor)
        build_leg.set_sample_io(src, dst)
        aq_plan_objs = build_leg.add()

        upstr_ops = []

        for s in src["Fragment"]:
            upstr_ops.append(prev_step_outputs.get(s))

        dnstr_op = build_leg.get_input_op()
        build_leg.wire_input_array(upstr_ops, dnstr_op)

        upstr_op = build_leg.get_output_op()

        cursor.incr_x()

        for i in range(n_seqs):
            qc_leg = SangerSeqLeg(plan_step, cursor)
            qc_leg.set_sample_io(src, dst)
            aq_plan_objs = qc_leg.add()
            dnstr_op = qc_leg.get_input_op()
            qc_leg.wire_ops(upstr_op, dnstr_op)
            cursor.incr_x()
            cursor.incr_y(qc_leg.length())

            if not prev_step_outputs.get(dst):
                plasmid_op = qc_leg.get_output_op()
                prev_step_outputs[dst] = plasmid_op
                plan.add_input_sample(dst, plasmid_op.output("Plasmid").sample)

        cursor.return_y()

cursor.set_xy(cursor.min_x, cursor.min_y)
cursor.decr_y()
cursor.set_home()

plan_step = plan.step_by_build_method("Yeast Transformation")
txns = plan_step.transformations

for txn in txns:
    src = txn['source']

    for dst in txn['destination']:
        build_leg = YeastTransformationLeg(plan_step, cursor)
        build_leg.set_sample_io(src, dst)
        aq_plan_objs = build_leg.add()
        build_leg.wire_plasmid()

        upstr_op = prev_step_outputs.get(src["Integrant"])
        dnstr_op = build_leg.get_input_op()
        wire_pair = [upstr_op.output("Plasmid"), dnstr_op.input("Integrant")]
        plan.aq_plan.add_wires([wire_pair])

        upstr_op = build_leg.get_output_op()
        prev_step_outputs[dst] = upstr_op

        cursor.incr_x()

        for i in range(n_qcs):
            qc_leg = YeastGenotypingLeg(plan_step, cursor)
            qc_leg.set_sample_io(src, dst)
            aq_plan_objs = qc_leg.add()
            dnstr_op = qc_leg.get_input_op()
            qc_leg.wire_ops(upstr_op, dnstr_op)
            cursor.incr_x()
            cursor.incr_y(qc_leg.length())

        cursor.return_y()


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
