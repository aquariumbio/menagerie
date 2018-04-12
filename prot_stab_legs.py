from aq_classes import Leg

class ProtStabLeg(Leg):
    def __init__(self, plan_step, source, destination, leg_order, aq_defaults_path):
        super().__init__(plan_step, source, destination, leg_order, aq_defaults_path)

        self.primary_handles = [
            'Yeast Culture',
            'Labeled Yeast Library',
            'Stored sample rep 1',
            'Stored sample rep 2'
        ]

        input_sample_uri = self.plan_step.get_inputs('DNA Library')[0]
        input_sample = self.ext_plan.input_samples[input_sample_uri]

        for h in self.primary_handles:
            self.sample_io[h] = input_sample

    def select_op(ops, ot_name):
        selected = [o for o in ops if o.operation_type.name == ot_name]
        if selected: return selected[0]

    def wire_to_prev(self, upstr_op, dnstr_op):
        wire_pair = self.get_wire_pair(upstr_op, dnstr_op)
        self.aq_plan.add_wires([wire_pair])
        self.propagate_sample(upstr_op, dnstr_op)

    def get_output_op(self):
        ops = self.aq_plan_objs['ops']
        output_op_name = 'Innoculate Yeast Library'
        ops = [o for o in ops if o.operation_type.name == output_op_name]
        if ops:
            return ops[0]


class OvernightLeg(ProtStabLeg):
    def __init__(self, plan_step, source, destination, leg_order, aq_defaults_path):
        super().__init__(plan_step, source, destination, leg_order, aq_defaults_path)

    def set_start_date(self, start_date):
        op = self.get_output_op()
        v = '{ "delay_until": "%s" }' % start_date
        op.set_field_value('Options', 'input', value=v)


class NaiveLeg(ProtStabLeg):
    def __init__(self, plan_step, source, destination, leg_order, aq_defaults_path):
        super().__init__(plan_step, source, destination, leg_order, aq_defaults_path)


class InductionLeg(ProtStabLeg):
    def __init__(self, plan_step, source, destination, leg_order, aq_defaults_path):
        super().__init__(plan_step, source, destination, leg_order, aq_defaults_path)


class SampleLeg(ProtStabLeg):
    def __init__(self, plan_step, source, destination, leg_order, aq_defaults_path):
        super().__init__(plan_step, source, destination, leg_order, aq_defaults_path)

        prot_samp = self.get_protease(self.source)
        prot_key = self.get_treatment_key()
        prot_conc = self.ext_plan.get_concentration(prot_key)
        self.sample_io['Protease'] = prot_samp
        self.sample_io['Protease Concentration'] = prot_conc

        ngs_samples = self.ext_plan.ngs_samples()

        if not self.destination in ngs_samples:
            ngs_ops = [
                'Innoculate Yeast Library',
                'Store Yeast Library Sample'
            ]
            self.sample_io['Sort?'] = 'no'
            self.params = [s for s in self.params if not s['name'] in ngs_ops]

    def get_protease(self, source):
        protease_inputs = self.plan_step.get_inputs('Protease')
        default = [self.ext_plan.default_protease]
        p = [x for x in self.source if x in protease_inputs] or default
        return self.ext_plan.input_samples[p[0]]

    def get_treatment_key(self):
        return self.destination.split('/')[-1]
