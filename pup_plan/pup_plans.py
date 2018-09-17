import json

import pydent
from pydent import models
from pydent.models import Sample

import plans
from plans import ExternalPlan, PlanStep

class PupPlan(ExternalPlan):

    input_list_names = {
        "partSamples": "Fragment",
        "vectorSamples": "Fragment",
        "templateSamples": "Plasmid",
        "primerSamples": "Primer",
        "yeastSamples" : "Yeast Strain"
    }

    def __init__(self, aq_plan_name, aq_instance):
        super().__init__(aq_plan_name, aq_instance)

        self.provision_samples()

        for step in self.plan["steps"]:
            build_method = step["parameters"]["buildMethod"]
            step_id = step["id"]

            if build_method == "PCR":
                dst_sample_type = "Fragment"
                step = PCRStep(self, step, step_id)

            elif build_method == "Gibson Assembly":
                dst_sample_type = "Plasmid"
                step = GibsonStep(self, step, step_id)

            elif build_method == "Yeast Transformation":
                dst_sample_type = "Yeast Strain"
                step = YeastTransformationStep(self, step, step_id)

            self.steps.append(step)

            for txn in step.transformations:
                for sample_name in txn["destination"]:
                    samples = self.get_samples(dst_sample_type, sample_name, txn["source"])
                    sample = samples[0]

                    self.input_samples[sample_name] = sample

    def step_by_build_method(self, build_method):
        return next(s for s in self.steps if s.build_method == build_method)

    def provision_samples(self):
        prov_step = [s for s in self.plan["steps"] if s["parameters"]["buildMethod"] == "Provision"][0]

        for list_name, sample_type in PupPlan.input_list_names.items():
            for sample in prov_step.get(list_name, []):
                sample_type = sample.get("sample_type") or sample_type
                sample["aqSamples"] = self.get_samples(sample_type, sample["name"])
                self.input_samples[sample["name"]] = sample["aqSamples"][0]

        self.plan["steps"].remove(prov_step)

    def add_input_sample(self, sample_name, sample):
        self.input_samples[sample_name] = sample

    def get_input_sample(self, sample_name):
        return self.input_samples.get(sample_name, sample_name)


class PupPlanStep(PlanStep):
    def __init__(self, plan, plan_step, step_id):
        super().__init__(plan, plan_step)
        self.plan = plan
        self.plan_step = plan_step
        self.step_id = step_id
        self.operator_type = plan_step["parameters"]["buildMethod"]
        self.build_method = self.operator_type
        self.transformations = []


class GoldenGateStep(PupPlanStep):
    def __init__(self, plan, plan_step, step_id):
        super().__init__(plan, plan_step, step_id)

        for d in plan_step["designs"]:
            txn = {"destination": [d["name"]]}
            src = list(d["partPositionMap"].values())
            src.append(d["vectorName"])
            txn["source"] = src
            self.transformations.append(txn)


class GibsonStep(PupPlanStep):
    def __init__(self, plan, plan_step, step_id):
        super().__init__(plan, plan_step, step_id)

        for design in plan_step["designs"]:
            txn = {"destination": [design.pop("name")]}
            txn["source"] = design
            self.transformations.append(txn)


class PCRStep(PupPlanStep):
    def __init__(self, plan, plan_step, step_id):
        super().__init__(plan, plan_step, step_id)

        for design in plan_step["designs"]:
            txn = {"destination": [design.pop("name")]}
            txn["source"] = design
            self.transformations.append(txn)


class YeastTransformationStep(PupPlanStep):
    def __init__(self, plan, plan_step, step_id):
        super().__init__(plan, plan_step, step_id)

        for design in plan_step["designs"]:
            txn = {"destination": [design.pop("name")]}
            txn["source"] = design
            self.transformations.append(txn)
