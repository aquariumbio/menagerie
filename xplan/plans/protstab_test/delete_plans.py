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

plan_ids = [
    "104696","104695","104694","104693","104692","104691","104690","104689"
]

for plan_id in plan_ids:
    plan = session.Plan.find(plan_id)
    plan.delete()
