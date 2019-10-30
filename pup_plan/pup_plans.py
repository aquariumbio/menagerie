import json

import pydent
from pydent import models
from pydent.models import Sample

import plans
from plans import ExternalPlan, PlanStep, Transformation
import plasmid_assembly_legs
from plasmid_assembly_legs import GibsonLeg, SangerSeqLeg, PCRLeg
from plasmid_assembly_legs import YeastTransformationLeg, YeastGenotypingLeg

class PupPlan(ExternalPlan):
    """
    Interface for working with the Aquarium Session and Plan models.
    Uses JSON schema derived from BU/SAIL Puppeteer schema.
    """

    def __init__(self, aq_plan_name, aq_instance):
        """
        In addition to super(), populates self.steps with new instances
        of PlanStep (PCRStep, GibsonStep or YeastTransformationStep).

        :param aq_plan_name: name of folder containing configuration files
            Also used as the name of the Plan record in Aquarium
        :type aq_plan_name: str
        :param aq_instance: the instance of Aquarium to use
            Corresponds to a key in the config.yml file
        :type aq_instance: str
        :return: new PupPlan
        """
        super().__init__(aq_plan_name, aq_instance)

        self.provision_samples()

        # TODO: This is very similar to the corresponding block in XPlan. Extract.
        # Create PlanStep objects based on operator type
        for step in self.plan["steps"]:
            build_method = step["type"]
            step_id = step["id"]

            if build_method == "pcr":
                dst_sample_type = "Fragment"
                step = PCRStep(self, step)

            elif build_method == "gibson":
                dst_sample_type = "Plasmid"
                step = GibsonStep(self, step)

            elif build_method == "yeast_transformation":
                dst_sample_type = "Yeast Strain"
                step = YeastTransformationStep(self, step)

            self.steps.append(step)

            # Why is this block not also in XPlan?
            for txn in step.transformations:
                for sample_name in txn["destination"]:
                    samples = self.get_samples(dst_sample_type, sample_name, txn["source"])
                    sample = samples[0]

                    self.input_samples[sample_name] = sample

    # TODO: Maybe make this return a list?
    # This seems to correspond to operator type in XPlan. Harmonize?
    def step_by_build_method(self, build_method):
        """
        Returns the first step of the specified build_method.

        :param build_method: the build method key
        :type build_method: str
        :return: PlanStep
        """
        return next(s for s in self.steps if s.build_method == build_method)

    # This seems structurally similar to what is going on in
    # self.plan_params['input_samples'] for XPlan
    def provision_samples(self):
        """Finds all the input samples for the PupPlan."""
        prov_step = [s for s in self.plan["steps"] if s["type"] == "provision"][0]

        for sample in prov_step.get("samples", []):
            print(sample)
            sample_type = sample.get("sample_type") or sample_type
            aq_samples = self.get_samples(sample_type, sample["name"])
            self.input_samples[sample["name"]] = aq_samples[0]

        # Is this wise or necessary?
        # self.plan["steps"].remove(prov_step)


class PupPlanStep(PlanStep):
    def __init__(self, plan, plan_step):
        super().__init__(plan, plan_step)
        self.plan = plan
        self.plan_step = plan_step

        self.step_id = self.plan_step['id']
        self.name = self.plan_step.get('name')
        self.operator_type = plan_step["type"]
        
        # It would be good to harmonize this with the XPlan schema
        self.operator = self.plan_step

        self.transformations = []
        for txn in self.operator.get('transformations', []):
            self.transformations.append(PupPlanTransformation(self, txn))

        # self.measurements = []
        # for msmt in self.operator.get('measurements', []):
        #     self.measurements.append(XPlanMeasurement(self, msmt))

        # self.measured_samples = [m.source for m in self.measurements]

        self.output_operations = {}

        self.build_method = self.operator_type


class GoldenGateStep(PupPlanStep):
    def __init__(self, plan, plan_step):
        super().__init__(plan, plan_step)


class GibsonStep(PupPlanStep):
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


class PCRStep(PupPlanStep):
    def __init__(self, plan, plan_step):
        super().__init__(plan, plan_step)

    def create_step(self, cursor, step_outputs={}):
        for txn in self.transformations:
            src = txn['source']

            for dst in txn['destination']:
                sample_type = self.plan.input_samples.get(src['Template']).sample_type.name

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

class YeastTransformationStep(PupPlanStep):
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

class PupPlanTransformation(Transformation):
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
