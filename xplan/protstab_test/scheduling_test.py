import sys
sys.path.append('/Users/devin/work/trident')
sys.path.append('/Users/devin/work/ext-plan-pydent')

import pydent
from pydent import AqSession, models
from pydent.models import Plan, Sample, DataAssociation

import json
import copy
import os

import warnings
warnings.filterwarnings('ignore')

# ### Create an Aquarium session
user = "devin"
password = "Q11m#Rd#nRQ^IsCoW80Rn5XDm&xjSDh!"
nursery = AqSession(user, password, "http://52.27.43.242:81/")
production = None #AqSession(user, password, "http://52.27.43.242/")

# Use this to switch between nursery and production
session = nursery

# Test the session
me = session.User.where({'login': user})[0]
print('Hello %s\n' % me.name)

p = Plan('Scheduler Test')

op_type = session.OperationType.where({
    'name': 'Innoculate Yeast Library',
    "deployed": True
})[0]

op1 = op_type.instance()
op2 = op_type.instance()
op1.connect_to_session(session)
op2.connect_to_session(session)

op1.set_field_value('Options', 'input', value='{ "delay_until": "04/03/18" }')
op2.set_field_value('Options', 'input', value='{ "delay_until": "04/04/18" }')

p.add_operations([op1, op2])

p.connect_to_session(session)
p.create()
