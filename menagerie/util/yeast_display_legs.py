from util.plans import Leg

class YeastDisplayLeg(Leg):

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
        input_sample = self.plan.input_sample(input_sample_uri)
        self.set_yeast_from_sample(input_sample)

    def set_yeast_from_sample(self, input_sample):
        for h in self.primary_handles:
            self.sample_io[h] = input_sample

    def get_innoculate_op(self):
        return self.select_op('Innoculate Yeast Library')

    # def set_uri(self, ot_name, obj):
    #     op = self.select_op(ot_name)
    #     obj.get('sample')


class OvernightLeg(YeastDisplayLeg):

    leg_order = ['Innoculate Yeast Library']

    def __init__(self, plan_step, cursor):
        super().__init__(plan_step, cursor)


class MixCulturesLeg(YeastDisplayLeg):

    leg_order = ['Mix Cultures']

    def __init__(self, plan_step, cursor):
        super().__init__(plan_step, cursor)

    def set_components(self, library_composition):
        self.sample_io["Component Yeast Culture"] = library_composition["components"]
        self.sample_io["Proportions"] = str(library_composition["proportions"])

    def wire_ops(self, src, dst):
        self.plan.add_wire(src, dst)


class NaiveLeg(YeastDisplayLeg):

    leg_order = ['Store Yeast Library Sample']

    def __init__(self, plan_step, cursor):
        super().__init__(plan_step, cursor)


class InductionLeg(YeastDisplayLeg):

    leg_order = ['Dilute Yeast Library']

    def __init__(self, plan_step, cursor):
        super().__init__(plan_step, cursor)


class TreatmentLeg(YeastDisplayLeg):

    leg_order = []

    treatment_sample_types = ['Protease', 'Biotinylated Binding Target']

    def __init__(self, plan_step, cursor):
        super().__init__(plan_step, cursor)

    def set_antibody(self, source):
        antibody = [s for s in source if s.get("sample_type") == "Antibody"]

        if antibody:
            key = self.plan_step.sample_key(antibody[0])
            print("##### " + key)
            antibody_sample = self.plan.input_sample(key)
            self.sample_io['Antibody'] = antibody_sample

    def set_protease(self, source):
        for sample_type in self.treatment_sample_types:
            protease_inputs = self.plan_step.get_inputs(sample_type)
            if protease_inputs: break

        protease = [s for s in source if self.plan_step.sample_key(s) in protease_inputs]

        if protease:
            s = protease[0]
            prot_samp = self.plan.input_sample(self.plan_step.sample_key(s))
            prot_conc = s['concentration']
            self.sample_io['Protease'] = prot_samp
            self.sample_io['Protease Concentration'] = prot_conc

            print(prot_samp.name + " " + str(prot_conc))

        else:
            raise "protease not found"


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
