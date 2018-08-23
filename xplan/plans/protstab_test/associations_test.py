import sys
sys.path.append('/Users/devin/work/trident')
sys.path.append('/Users/devin/work/ext-plan-pydent')

import pydent
from pydent import AqSession, models
from pydent.models import Plan

import json
import copy
import os

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

p = Plan('Associations Test')

op_type = session.OperationType.where({
    'name': 'Challenge and Label',
    "deployed": True
})[0]

op1 = op_type.instance()
op1.connect_to_session(session)

op2 = op_type.instance()
op2.connect_to_session(session)

p.add_operations([op1, op2])

p.connect_to_session(session)
p.create()
p.associate('plan_test', 'This is a plan data association')

da1 = op1.associate('destination', '["https:\/\/hub.sd2e.org\/user\/sd2e\/biofab_protstab_Q2_1\/s906_R1094\/1"]')
da2 = op2.associate('test', 12345)

assert op1.id == p.operations[0].id
assert op2.id == p.operations[1].id

print(da1.object)
print(op1.data_associations[0].object)

print(da2.object)
print(op2.data_associations[0].object)

print([da.object for da in p.all_data_associations()])