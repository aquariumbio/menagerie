from aq_classes import Leg

class GoldenGateLeg(Leg):

    primary_handles = [
        'Plasmid',
        'Transformed E Coli',
        'Plate',
        'Overnight',
        'Plasmid for Sequencing'
    ]

    leg_order = [
        'Assemble NEB Golden Gate',
        'Transform Cells from Stripwell',
        'Plate Transformed Cells',
        'Check Plate',
        'Make Overnight Suspension',
        'Make Miniprep',
        'Send to Sequencing',
        'Upload Sequencing Results'
    ]

    def __init__(self, plan_step, cursor):
        super().__init__(plan_step, cursor)

    def set_sample_io(self, source, destination):
        self.sample_io['Plasmid'] = self.ext_plan.input_samples.get(destination)

        backbones = [s for s in source if s.startswith('Vector')] or [None]
        self.sample_io['Backbone'] = self.ext_plan.input_samples.get(backbones[0])

        inserts = [s for s in source if not s.startswith('Vector')]
        self.sample_io['Inserts'] = [self.ext_plan.input_samples.get(i) for i in inserts]
