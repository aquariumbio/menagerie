from aq_classes import Leg

class CloningLeg(Leg):

    primary_handles = [
        'Plasmid',
        'Transformed E Coli',
        'Plate',
        'Overnight',
        'Plasmid for Sequencing'
    ]

    def __init__(self, plan_step, cursor):
        super().__init__(plan_step, cursor)


class GoldenGateLeg(CloningLeg):

    leg_order = [
        'Assemble NEB Golden Gate',
        'Transform Cells from Stripwell',
        'Plate Transformed Cells',
        'Check Plate'
    ]

    def __init__(self, plan_step, cursor):
        super().__init__(plan_step, cursor)

    def set_sample_io(self, source, destination):
        self.sample_io['Plasmid'] = self.ext_plan.input_samples.get(destination)

        backbones = [s for s in source if s.startswith('Vector')] or [None]
        self.sample_io['Backbone'] = self.ext_plan.input_samples.get(backbones[0])

        inserts = [s for s in source if not s.startswith('Vector')]
        self.sample_io['Inserts'] = [self.ext_plan.input_samples.get(i) for i in inserts]


class GibsonLeg(CloningLeg):

    leg_order = [
        'Assemble Plasmid',
        'Transform Cells',
        'Plate Transformed Cells',
        'Check Plate'
    ]

    def __init__(self, plan_step, cursor):
        super().__init__(plan_step, cursor)

    def set_sample_io(self, source, destination):
        self.sample_io['Assembled Plasmid'] = self.ext_plan.input_samples.get(destination)

        fragments = [s for s in source if s.startswith('Fragment')] or [None]
        self.sample_io['Fragment'] = [self.ext_plan.input_samples.get(f) for f in fragments]


class SangerSeqLeg(CloningLeg):

    leg_order = [
        'Make Overnight Suspension',
        'Make Miniprep',
        'Send to Sequencing',
        'Upload Sequencing Results'
    ]

    def __init__(self, plan_step, cursor):
        super().__init__(plan_step, cursor)

    def set_sample_io(self, source, destination):
        for h in self.primary_handles:
            self.sample_io[h] = self.ext_plan.input_samples.get(destination)


class PCRLeg(CloningLeg):

    leg_order = [
        'Make PCR Fragment',
        'Run Gel',
        'Extract Gel Slice',
        'Purify Gel Slice'
    ]

    def __init__(self, plan_step, cursor):
        super().__init__(plan_step, cursor)
