import sys
import os
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# trident_path = '/Users/devin/Documents/work/trident'
# sys.path.append(trident_path)
ext_plan_path = '/Users/devin/Documents/work/ext-plan-pydent'
sys.path.append(ext_plan_path)

from aq_classes import Cursor, Leg
from xplan.xplans import XPlan
from prot_stab_legs import OvernightLeg, NaiveLeg, InductionLeg, MixCulturesLeg
from prot_stab_legs import SortLeg, FlowLeg, ProtStabLeg

from plan_tests import test_plan
from user_input import get_input

inputs = get_input()

start_date = inputs['start_date']
plan = XPlan(inputs['aq_plan_name'], inputs['aq_instance'])

# This keeps track of where to put the next operation in the GUI.
cursor = Cursor(x=64, y=1168)

for step_id in plan.step_ids(plan.get_steps_by_type('protstab_round')):
    plan_step = plan.step(step_id)

    if int(step_id) > 1:
        prev_plan_step = plan.step(step_id - 1)
        prev_step_outputs = prev_plan_step.output_operations
    else:
        prev_step_outputs = {}

    new_inputs = {}

    for input_yeast in plan_step.yeast_inputs():
        st_name = plan.input_samples[input_yeast].sample_type.name
        is_library = st_name == 'DNA Library'

        if not prev_step_outputs.get(input_yeast):
            cursor.incr_y(2)
            container_opt = 'library start' if is_library else 'control'

            overnight_samples = []
            library_composition = plan.input_samples.get("library_composition")
            mix_cultures = is_library and library_composition

            if mix_cultures:
                cursor.incr_y()
                for comp in library_composition["components"]:
                    overnight_samples.append(comp)

            else:
                overnight_samples.append(plan.input_samples[input_yeast])

            overnight_ops = {}

            for os in overnight_samples:
                subs = (input_yeast, str(start_date.date()))
                print("Planning innoculation of %s on %s" % subs)

                overnight_leg = OvernightLeg(plan_step, cursor)
                overnight_leg.set_yeast_from_sample(os)
                overnight_leg.add(container_opt)
                overnight_leg.set_start_date(start_date.date())

                overnight_ops[os.name] = overnight_leg.get_innoculate_op()

                cursor.incr_x()
                cursor.incr_y()

            if mix_cultures:
                cursor.decr_y()
                cursor.return_x()
                mix_cultures_leg = MixCulturesLeg(plan_step, cursor)
                mix_cultures_leg.set_yeast(input_yeast)
                mix_cultures_leg.set_components(library_composition)
                mix_cultures_leg.add(container_opt)

                mix_cultures_op = mix_cultures_leg.select_op('Mix Cultures')
                culture_inputs = mix_cultures_op.input_array("Component Yeast Culture")

                for culture in culture_inputs:
                    op = overnight_ops[culture.sample.name]
                    mix_cultures_leg.wire_to_prev(op.output("Yeast Culture"), culture)

                upstr_op = mix_cultures_op

            else:
                upstr_op = overnight_leg.select_op('Innoculate Yeast Library')

            cursor.return_y()

            if input_yeast in plan.ngs_samples:
                cursor.decr_y(SortLeg.length() - NaiveLeg.length())
                naive_leg = NaiveLeg(plan_step, cursor)
                naive_leg.set_yeast(input_yeast)
                naive_leg.add('library')
                cursor.return_y()

                dnstr_op = naive_leg.select_op('Store Yeast Library Sample')
                naive_leg.wire_to_prev(upstr_op, dnstr_op)

            new_inputs[input_yeast] = upstr_op

        upstr_op = prev_step_outputs.get(input_yeast) or new_inputs.get(input_yeast)
        input_sample = upstr_op.output('Yeast Culture').sample

        cursor.set_x(upstr_op.x)

        if int(step_id) > 1 and is_library:
            cursor.decr_x(2)
        else:
            cursor.incr_x()

        cursor.return_y()

        cursor.incr_y(2)
        container_opt = 'library' if is_library else 'control'
        induction_leg = InductionLeg(plan_step, cursor)
        induction_leg.set_yeast(input_yeast)
        induction_leg.add(container_opt)
        cursor.return_y()

        dnstr_op = induction_leg.select_op('Dilute Yeast Library')
        induction_leg.wire_to_prev(upstr_op, dnstr_op)

        txns = [t for t in plan_step.transformations if input_yeast in t.source_samples()]

        partitioned = {}

        for t in txns:
            sample = t.protease().get('sample', '')

            if not partitioned.get(sample):
                partitioned[sample] = []

            partitioned[sample].append(t)

        proteases = list(partitioned.keys())
        proteases.sort()

        for p in proteases:
            txns = partitioned[p]
            txns.sort(key=lambda t: t.protease().get('concentration', 0))

            for txn in txns:
                src = txn.source
                for dst in txn.destination:
                    ngs_sample = dst['sample'] in plan.ngs_samples
                    if ngs_sample:
                        this_leg = SortLeg(plan_step, cursor)
                    else:
                        this_leg = FlowLeg(plan_step, cursor)

                    this_leg.set_yeast(input_yeast)
                    this_leg.set_protease(src)
                    # this_leg.set_uri(src, dst)

                    # This is not a good way to set these variables
                    if ngs_sample:
                        this_leg.sample_io['Control?'] = 'no'
                    else:
                        yeast_name = this_leg.sample_io['Labeled Yeast Library'].name
                        if yeast_name == 'EBY100 + pETcon3':
                            this_leg.sample_io['Control?'] = 'autofluorescence'
                        elif yeast_name == 'AMA1-best':
                            if this_leg.sample_io['Protease Concentration'] == 0:
                                this_leg.sample_io['Control?'] = 'high-fitc'
                            else:
                                this_leg.sample_io['Control?'] = 'protease'

                    this_leg.add(container_opt)

                    upstr_op = induction_leg.select_op('Dilute Yeast Library')
                    dnstr_op = this_leg.select_op('Challenge and Label')
                    this_leg.wire_to_prev(upstr_op, dnstr_op)

                    # data_assoc = { 'destination': dst['sample'] }
                    # plan.update_temp_data_assoc(dnstr_op, data_assoc)

                    output_op = this_leg.get_innoculate_op()

                    if output_op:
                        plan_step.add_output_operation(dst['sample'], output_op)
                        plan.add_input_sample(dst['sample'], output_op.output('Yeast Culture').sample)

                    cursor.incr_x()
                    cursor.return_y()

            cursor.incr_x(0.25)

    cursor.update_max_x()
    # cursor.return_x()
    cursor.decr_y(SortLeg.length() + 3)
    cursor.set_y_home()

    if start_date.weekday() == 4:
        incr = 3
    else:
        incr = 2

    start_date += timedelta(days=incr)

    print(plan_step.name + ' complete')
    print()

plan.launch_aq_plan()
plan.add_data_associations()

url = plan.aq_plan.session.url + "/plans?plan_id={}".format(plan.aq_plan.id)
print("Created Plan: {}".format(url))
print("{} total operations.".format(len(plan.aq_plan.operations)))
print("{} total wires.".format(len(plan.aq_plan.wires)))

# out_path = os.path.join(plan.plan_path, 'dump.json')
# ref_path = os.path.join(plan.plan_path, 'dump-ref.json')
# test_plan(plan, out_path, ref_path)
# print("Test passed!")

delete = input("Do you want to delete this plan? (y/n) ")
if delete == 'y' or delete == 'Y':
    plan.aq_plan.delete()
