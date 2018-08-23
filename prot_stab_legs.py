from aq_classes import Leg

class ProtStabLeg(Leg):

    leg_order = []

    primary_handles = [
        'Yeast Culture',
        'Labeled Yeast Library',
        'Stored sample rep 1',
        'Stored sample rep 2'
    ]

    def __init__(self, plan_step, cursor):
        super().__init__(plan_step, cursor)

    def set_yeast(self, input_sample_uri):
        input_sample = self.ext_plan.input_samples[input_sample_uri]

        for h in self.primary_handles:
            self.sample_io[h] = input_sample

    @classmethod
    def length(cls):
         return len(cls.leg_order)

    # This should be renamed because it doesn't matter which Leg it is called on.
    def wire_to_prev(self, upstr_op, dnstr_op):
        wire_pair = self.get_wire_pair(upstr_op, dnstr_op)
        self.aq_plan.add_wires([wire_pair])
        self.propagate_sample(upstr_op, dnstr_op)

    def get_innoculate_op(self):
        return self.select_op('Innoculate Yeast Library')

    def set_uri(self, ot_name, obj):
        op = self.select_op(ot_name)
        obj.get('sample')


class OvernightLeg(ProtStabLeg):

    leg_order = ['Innoculate Yeast Library']

    def __init__(self, plan_step, cursor):
        super().__init__(plan_step, cursor)


class NaiveLeg(ProtStabLeg):

    leg_order = ['Store Yeast Library Sample']

    def __init__(self, plan_step, cursor):
        super().__init__(plan_step, cursor)


class InductionLeg(ProtStabLeg):

    leg_order = ['Dilute Yeast Library']

    def __init__(self, plan_step, cursor):
        super().__init__(plan_step, cursor)


class TreatmentLeg(ProtStabLeg):

    leg_order = []

    def __init__(self, plan_step, cursor):
        super().__init__(plan_step, cursor)

    def set_protease(self, source):
        protease_inputs = self.plan_step.get_inputs('Protease')
        p = [s for s in source if s.get('sample') in protease_inputs]

        if p:
            prot_samp =  self.ext_plan.input_samples[p[0]['sample']]
            prot_conc = p[0]['concentration']

        else:
            prot_samp =  self.ext_plan.input_samples[self.ext_plan.default_protease]
            prot_conc = 0

        self.sample_io['Protease'] = prot_samp
        self.sample_io['Protease Concentration'] = prot_conc

        print(prot_samp.name + " " + str(prot_conc))


class SortLeg(TreatmentLeg):

    leg_order = (
        'Challenge and Label',
        'Sort Yeast Display Library',
        'Innoculate Yeast Library',
        'Store Yeast Library Sample'
    )

    def __init__(self, plan_step, cursor):
        super().__init__(plan_step, cursor)

        self.sample_io['Sort?'] = 'yes'


class FlowLeg(TreatmentLeg):

    leg_order = (
        'Challenge and Label',
        'Sort Yeast Display Library'
    )

    def __init__(self, plan_step, cursor):
        super().__init__(plan_step, cursor)

        self.sample_io['Sort?'] = 'no'
