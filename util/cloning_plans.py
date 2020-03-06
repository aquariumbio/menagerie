import json

import pydent
from pydent import models
from pydent.models import Sample

from util.plans import ExternalPlan, PlanStep, Transformation, get_obj_by_attr
from util.plasmid_assembly_legs import GibsonLeg, SangerSeqLeg, PCRLeg
from util.plasmid_assembly_legs import YeastTransformationLeg, YeastGenotypingLeg

class CloningPlan(ExternalPlan):
    """
    Interface for working with the Aquarium Session and Plan models.
    Originally based on JSON schema derived from BU/SAIL Puppeteer schema.
    """

    def __init__(self, plan_path, aq_instance, aq_plan_name=None):
        """
        In addition to super(), populates self.steps with new instances
        of PlanStep (PCRStep, GibsonStep or YeastTransformationStep).

        :param plan_path: name of folder containing configuration files
            Also used as the name of the Plan record in Aquarium
        :type plan_path: str
        :param aq_instance: the instance of Aquarium to use
            Corresponds to a key in the secrets.json file
        :type aq_instance: str
        :return: new CloningPlan
        """
        super().__init__(plan_path, aq_instance, aq_plan_name)

        for step in self.steps:
            dst_sample_type = self.destination_sample_type(step.type)
            # Why is this block not also in XPlan?
            for txn in step.transformations:
                for dst in txn.destination:
                    samples = self.get_samples(dst_sample_type, dst["name"], txn.source)
                    sample = samples[0]

                    self.add_input_sample(dst["name"], sample)

    def initialize_step(self, step_data):
        step = super().initialize_step(step_data)

        if not step:
            step_type = step_data["type"]

            if step_type == "pcr":
                step = PCRStep(self, step_data)

            elif step_type == "gibson":
                step = GibsonStep(self, step_data)

            elif step_type == "yeast_transformation":
                step = YeastTransformationStep(self, step_data)

            else:
                step = None

        return step

    def destination_sample_type(self, step_type):
        if step_type == "pcr":
            dst_sample_type = "Fragment"

        elif step_type == "gibson":
            dst_sample_type = "Plasmid"

        elif step_type == "yeast_transformation":
            dst_sample_type = "Yeast Strain"

        else:
            dst_sample_type = None

        return dst_sample_type


class CloningPlanStep(PlanStep):
    def __init__(self, plan, plan_step):
        super().__init__(plan, plan_step)

        for txn in self.operator.get('transformations', []):
            self.transformations.append(CloningPlanTransformation(self, txn))


class GoldenGateStep(CloningPlanStep):
    def __init__(self, plan, plan_step):
        super().__init__(plan, plan_step)


class GibsonStep(CloningPlanStep):
    def __init__(self, plan, plan_step):
        super().__init__(plan, plan_step)

    def create_step(self, cursor, n_qcs=1, step_outputs={}):
        for txn in self.transformations:
            src = txn.source
            fragment_src = [o for o in src if o["input_name"] == "Fragment"]
            fragment_src.sort(key=lambda s: step_outputs.get(s["name"]).x)

            for dst in txn.destination:
                build_leg = GibsonLeg(self, cursor)
                build_leg.set_sample_io(src, dst)
                build_leg.add()

                upstr_ops = []

                for s in fragment_src:
                    upstr_ops.append(step_outputs.get(s["name"]))

                dnstr_op = build_leg.get_input_op()
                # build_leg.wire_input_array(upstr_ops, dnstr_op)

                upstr_op = build_leg.get_output_op()

                cursor.incr_x()

                for i in range(n_qcs):
                    qc_leg = SangerSeqLeg(self, cursor)
                    qc_leg.set_sample_io(src, dst)
                    qc_leg.add()
                    dnstr_op = qc_leg.get_input_op()
                    qc_leg.wire_ops(upstr_op, dnstr_op)
                    cursor.incr_x()
                    cursor.incr_y(qc_leg.length())

                    if not step_outputs.get(dst["name"]):
                        plasmid_op = qc_leg.get_output_op()
                        step_outputs[dst["name"]] = plasmid_op
                        self.plan.add_input_sample(dst["name"], plasmid_op.output("Plasmid").sample)

                cursor.return_y()

        return step_outputs


class PCRStep(CloningPlanStep):
    def __init__(self, plan, plan_step):
        super().__init__(plan, plan_step)

    def create_step(self, cursor, step_outputs={}):
        for txn in self.transformations:
            src = txn.source
            template_src = get_obj_by_attr(src, "input_name", "Template")

            for dst in txn.destination:
                sample_type = self.plan.input_sample(template_src["name"]).sample_type.name

                if sample_type == "DNA Library":
                    container_opt = "dna_library"
                else:
                    container_opt = "plasmid_stock"

                build_leg = PCRLeg(self, cursor)
                build_leg.set_sample_io(src, dst)
                build_leg.add(container_opt)

                step_outputs[dst["name"]] = build_leg.get_output_op()
                cursor.incr_x()
                cursor.return_y()

        return step_outputs


class YeastTransformationStep(CloningPlanStep):
    def __init__(self, plan, plan_step):
        super().__init__(plan, plan_step)

    def create_step(self, cursor, n_qcs=1, step_outputs={}):
        for txn in self.transformations:
            src = txn.source
            integrant_src = get_obj_by_attr(src, "input_name", "Integrant")

            for dst in txn.destination:
                build_leg = YeastTransformationLeg(self, cursor)
                build_leg.set_sample_io(src, dst)
                build_leg.add()
                build_leg.wire_plasmid()

                upstr_op = step_outputs.get(integrant_src)
                dnstr_op = build_leg.get_input_op()
                wire_pair = [upstr_op.output("Plasmid"), dnstr_op.input("Integrant")]
                self.plan.aq_plan.add_wires([wire_pair])

                upstr_op = build_leg.get_output_op()
                step_outputs[dst] = upstr_op

                cursor.incr_x()

                for i in range(n_qcs):
                    qc_leg = YeastGenotypingLeg(self, cursor)
                    qc_leg.set_sample_io(src, dst)
                    qc_leg.add()
                    dnstr_op = qc_leg.get_input_op()
                    qc_leg.wire_ops(upstr_op, dnstr_op)
                    cursor.incr_x()
                    cursor.incr_y(qc_leg.length())

                cursor.return_y()

        return step_outputs


class CloningPlanTransformation(Transformation):
    def __init__(self, plan_step, transformation):
        super().__init__(plan_step, transformation)
