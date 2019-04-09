from plans import Leg, get_obj_by_name

class CloningLeg(Leg):

    primary_handles = [
        "Fragment",
        "Plasmid",
        "Transformed E Coli",
        "Plate",
        "Overnight",
        "Plasmid for Sequencing",
        "Assembled Plasmid",
        "Gel"
    ]

    def __init__(self, plan_step, cursor):
        super().__init__(plan_step, cursor)

    def set_sample_inputs(self, source):
        for handle, name in source.items():
            if isinstance(name, str):
                self.sample_io[handle] = self.ext_plan.get_input_sample(name)
            elif isinstance(name, list):
                samples = [self.ext_plan.get_input_sample(n) for n in name]
                self.sample_io[handle] = samples

    def set_sample_outputs(self, destination):
        for handle in self.primary_handles:
            self.sample_io[handle] = self.ext_plan.get_input_sample(destination)

    def set_sample_io(self, source, destination):
        self.set_sample_outputs(destination)
        self.set_sample_inputs(source)


class GoldenGateLeg(CloningLeg):

    leg_order = [
        {"name": "Assemble NEB Golden Gate", "category": "Cloning"},
        {"name": "Transform Cells from Stripwell", "category": "Cloning"},
        {"name": "Plate Transformed Cells", "category": "Cloning"},
        {"name": "Check Plate", "category": "Cloning"}
    ]

    def __init__(self, plan_step, cursor):
        super().__init__(plan_step, cursor)

    def set_sample_io(self, source, destination):
        self.sample_io["Plasmid"] = self.ext_plan.input_samples.get(destination)

        backbones = [s for s in source if s.startswith("Vector")] or [None]
        self.sample_io["Backbone"] = self.ext_plan.input_samples.get(backbones[0])

        inserts = [s for s in source if not s.startswith("Vector")]
        self.sample_io["Inserts"] = [self.ext_plan.input_samples.get(i) for i in inserts]


class GibsonLeg(CloningLeg):

    leg_order = [
        {"name": "Assemble Plasmid", "category": "Cloning"},
        {"name": "Transform Cells", "category": "Cloning"},
        {"name": "Plate Transformed Cells", "category": "Cloning"},
        {"name": "Check Plate", "category": "Cloning"}
    ]

    def __init__(self, plan_step, cursor):
        super().__init__(plan_step, cursor)

    def set_sample_io(self, source, destination):
        self.set_sample_outputs(destination)
        self.set_sample_inputs(source) # This needs to be set after outputs.
        self.sample_io["Comp Cells"] = self.session.Sample.where({"name": "DH5alpha"})[-1]


class SangerSeqLeg(CloningLeg):

    leg_order = [
        {"name": "Make Overnight Suspension", "category": "Cloning"},
        {"name": "Make Miniprep", "category": "Cloning"},
        {"name": "Send to Sequencing", "category": "Cloning"},
        {"name": "Upload Sequencing Results", "category": "Cloning"}
    ]

    def __init__(self, plan_step, cursor):
        super().__init__(plan_step, cursor)

    def get_output_op(self):
        return get_obj_by_name(self.op_data, "Make Miniprep")["operation"]


class PCRLeg(CloningLeg):

    leg_order = [
        {"name": "Make PCR Fragment", "category": "Cloning"},
        {"name": "Run Gel", "category": "Cloning"},
        {"name": "Extract Gel Slice", "category": "Cloning"},
        {"name": "Purify Gel Slice", "category": "Cloning"}
    ]

    def __init__(self, plan_step, cursor):
        super().__init__(plan_step, cursor)

    def add(self, container_opt=None):
        super().add(container_opt)
        self.cursor.return_y()
        self.cursor.incr_x()

        pour_gel_ot = self.session.OperationType.where({
            "name": "Pour Gel",
            "category": "Cloning",
            "deployed": True
        })
        pour_gel = pour_gel_ot[0].instance()
        pour_gel.x = self.cursor.x
        pour_gel.y = self.cursor.y

        run_gel = get_obj_by_name(self.op_data, "Run Gel")["operation"]
        gel_output = pour_gel.output("Lane")
        gel_input = run_gel.input("Gel")

        self.aq_plan.add_operations([pour_gel])
        self.aq_plan.add_wires([[gel_output, gel_input]])


class YeastTransformationLeg(CloningLeg):

    primary_handles = [
        "Yeast",
        "Yeast Strain",
        "Overnight",
        "Plate",
        "Streak Plate",
        "Transformation"
    ]

    dna_handles = [
        "Genetic Material",
        "Integrant",
        "Digested Plasmid"
    ]

    leg_order = [
        {"name": "Plasmid Digest", "category": "Yeast"},
        {"name": "Yeast Transformation", "category": "Yeast"},
        {"name": "Check Yeast Plate", "category": "Yeast"},
        {"name": "Streak on Media Plate", "category": "Library Cloning"},
        {"name": "Check Divided Yeast Plate", "category": "Yeast"},
        {"name": "Yeast Overnight Suspension from Collection", "category": "Yeast"},
        {"name": "Yeast Glycerol Stock", "category": "Yeast"}
    ]

    def __init__(self, plan_step, cursor):
        super().__init__(plan_step, cursor)

    def set_sample_io(self, source, destination):
        super().set_sample_io(source, destination)

        for h in self.dna_handles:
            self.sample_io[h] = self.ext_plan.input_samples.get(source["Integrant"])

        self.sample_io["Parent"] = self.ext_plan.input_samples.get(source["Parent"])

    def get_output_op(self):
        return get_obj_by_name(self.op_data, "Check Yeast Plate")["operation"]

    def wire_plasmid(self):
        upstr_fv = self.select_op("Plasmid Digest").output("Digested Plasmid")
        dnstr_fv = self.select_op("Yeast Transformation").input("Genetic Material")
        self.aq_plan.add_wires([[upstr_fv, dnstr_fv]])


class YeastGenotypingLeg(CloningLeg):

    primary_handles = [
        "Lysate",
        "Plate",
        "Template",
        "PCR"
    ]

    leg_order = [
        {"name": "Yeast Lysate", "category": "Yeast"},
        {"name": "Colony PCR", "category": "Yeast"},
        {"name": "Fragment Analyzing", "category": "Yeast"}
    ]

    def __init__(self, plan_step, cursor):
        super().__init__(plan_step, cursor)

    # def set_sample_io(self, source, destination):
    #     for h in self.primary_handles:
    #         self.sample_io[h] = self.ext_plan.input_samples.get(destination)
