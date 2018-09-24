from plans import Leg

class DNASeqLeg(Leg):

    primary_handles = [
            "Yeast Library",
            "Plasmid Library",
            "Zymoprepped sample",
            "Exonucleased sample",
            "Template",
            "Fragment",
            "Gel",
            "qPCR sample in",
            "qPCR sample out",
            "DNA library in",
            "DNA library out"
    ]

    def __init__(self, plan_step, cursor):
        super().__init__(plan_step, cursor)

    def set_yeast(self, input_sample_uri):
        input_sample = self.ext_plan.input_samples[input_sample_uri]
        self.set_yeast_from_sample(input_sample)

    def set_yeast_from_sample(self, input_sample):
        for h in self.primary_handles:
            self.sample_io[h] = input_sample

    def set_sample_io(self, io_obj):
        self.sample_io = { **self.sample_io, **io_obj }


class ExtractDNALeg(DNASeqLeg):

    leg_order = [
        {"name": "Treat With Zymolyase", "category": "Next Gen Prep"},
        {"name": "Extract Plasmid", "category": "Next Gen Prep"},
        {"name": "Digest Genomic DNA", "category": "Next Gen Prep"}
    ]

    def __init__(self, plan_step, cursor):
        super().__init__(plan_step, cursor)


class QPCRLeg(DNASeqLeg):

    leg_order = [
        {"name": "Make qPCR Fragment", "category": "Next Gen Prep"},
        {"name": "Run Pre-poured Gel", "category": "Next Gen Prep"},
        {"name": "Extract Gel Slice (Advanced)", "category": "Next Gen Prep"},
        {"name": "Purify Gel Slice (Advanced)", "category": "Library Cloning"}
    ]

    def __init__(self, plan_step, cursor):
        super().__init__(plan_step, cursor)


class DiluteLibraryLeg(DNASeqLeg):

    leg_order = [
        {"name": "Qubit concentration", "category": "Next Gen Prep"},
        {"name": "Dilute to 4nM", "category": "Next Gen Prep"}
    ]

    def __init__(self, plan_step, cursor):
        super().__init__(plan_step, cursor)