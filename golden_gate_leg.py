from aq_classes import Leg, get_op

class GoldenGateLeg(Leg):
    def __init__(self, plan_step, source, destination, leg_order, aq_defaults_path):
        super().__init__(plan_step, source, destination, leg_order, aq_defaults_path)

        self.primary_handles = [
            'Plasmid',
            'Transformed E Coli',
            'Plate',
            'Overnight',
            'Plasmid for Sequencing'
        ]

        self.sample_io['Plasmid'] = self.ext_plan.input_samples.get(destination)

        backbones = [s for s in source if s.startswith('Vector')] or [None]
        self.sample_io['Backbone'] = self.ext_plan.input_samples.get(backbones[0])
        inserts = [s for s in source if not s.startswith('Vector')]
        self.sample_io['Inserts'] = [self.ext_plan.input_samples.get(i) for i in inserts]
