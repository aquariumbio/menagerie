import json

import pydent
from pydent import models
from pydent.models import Sample

from util.plans import ExternalPlan, PlanStep, Transformation
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
            Corresponds to a key in the config.yml file
        :type aq_instance: str
        :return: new CloningPlan
        """
        super().__init__(plan_path, aq_instance, aq_plan_name)

        # self.provision_samples()

        for step in self.steps:
            dst_sample_type = self.destination_sample_type(step["type"])
            # Why is this block not also in XPlan?
            for txn in step.transformations:
                for sample_name in txn["destination"]:
                    samples = self.get_samples(dst_sample_type, sample_name, txn["source"])
                    sample = samples[0]

                    self.add_input_sample(sample_name, sample)

    def initialize_step(self, step_data):
        super().initialize_step(step_data)

        step_type = step_data["type"]

        if step_type == "pcr":
            step = PCRStep(self, step_data)

        elif step_type == "gibson":
            step = GibsonStep(self, step_data)

        elif step_type == "yeast_transformation":
            step = YeastTransformationStep(self, step_data)

        else:
            step = CloningPlanStep(self, step_data)

        return step

    def destination_sample_type(self, step_type):
        if step_type == "pcr":
            dst_sample_type = "Fragment"

        elif step_type == "gibson":
            dst_sample_type = "Plasmid"

        elif step_type == "yeast_transformation":
            dst_sample_type = "Yeast Strain"

        return dst_sample_type


class CloningPlanStep(PlanStep):
    def __init__(self, plan, plan_step):
        super().__init__(plan, plan_step)
        self.plan = plan
        self.plan_step = plan_step

        self.step_id = self.plan_step['id']
        self.name = self.plan_step.get('name')
        self.operator_type = plan_step["type"]
        
        # It would be good to harmonize this with the YeastDisplayPlan schema
        self.operator = self.plan_step

        self.transformations = []
        for txn in self.operator.get('transformations', []):
            self.transformations.append(CloningPlanTransformation(self, txn))

        # self.measurements = []
        # for msmt in self.operator.get('measurements', []):
        #     self.measurements.append(YeastDisplayPlanMeasurement(self, msmt))

        # self.measured_samples = [m.source for m in self.measurements]

        self.output_operations = {}

        self.step_type = self.operator_type


class GoldenGateStep(CloningPlanStep):
    def __init__(self, plan, plan_step):
        super().__init__(plan, plan_step)


class GibsonStep(CloningPlanStep):
    def __init__(self, plan, plan_step):
        super().__init__(plan, plan_step)

    def create_step(self, cursor, n_qcs=1, step_outputs={}):
        for txn in self.transformations:
            src = txn['source']
            src["Fragment"].sort(key=lambda s: step_outputs.get(s).x)

            for dst in txn['destination']:
                build_leg = GibsonLeg(self, cursor)
                build_leg.set_sample_io(src, dst)
                build_leg.add()

                upstr_ops = []

                for s in src["Fragment"]:
                    upstr_ops.append(step_outputs.get(s))

                dnstr_op = build_leg.get_input_op()
                build_leg.wire_input_array(upstr_ops, dnstr_op)

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

                    if not step_outputs.get(dst):
                        plasmid_op = qc_leg.get_output_op()
                        step_outputs[dst] = plasmid_op
                        self.plan.add_input_sample(dst, plasmid_op.output("Plasmid").sample)

                cursor.return_y()

        return step_outputs


class PCRStep(CloningPlanStep):
    def __init__(self, plan, plan_step):
        super().__init__(plan, plan_step)

    def create_step(self, cursor, step_outputs={}):
        for txn in self.transformations:
            src = txn['source']

            for dst in txn['destination']:
                sample_type = self.plan.input_sample(src['Template']).sample_type.name

                if sample_type == "DNA Library":
                    container_opt = "dna_library"
                else:
                    container_opt = "plasmid_stock"

                build_leg = PCRLeg(self, cursor)
                build_leg.set_sample_io(src, dst)
                build_leg.add(container_opt)

                step_outputs[dst] = build_leg.get_output_op()
                cursor.incr_x()
                cursor.return_y()

        return step_outputs

class YeastTransformationStep(CloningPlanStep):
    def __init__(self, plan, plan_step):
        super().__init__(plan, plan_step)

    def create_step(self, cursor, n_qcs=1, step_outputs={}):
        for txn in self.transformations:
            src = txn['source']

            for dst in txn['destination']:
                build_leg = YeastTransformationLeg(self, cursor)
                build_leg.set_sample_io(src, dst)
                build_leg.add()
                build_leg.wire_plasmid()

                upstr_op = step_outputs.get(src["Integrant"])
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
        self.source = self.format(transformation['source'])
        self.destination = self.format(transformation['destination'])

    def source_samples(self):
        return [x['sample'] for x in self.source]

    def destination_samples(self):
        return [x['sample'] for x in self.destination]

    @staticmethod
    def format(element):
        if isinstance(element, list):
            return [{ 'sample': e } if isinstance(e, str) else e for e in element]

        elif isinstance(element, dict):
            return [element]

        elif isinstance(element, str):
            return [{ 'sample': element }]

        else:
            raise Exception('Format of %s not recognized' % str(element))
