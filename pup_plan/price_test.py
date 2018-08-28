import sys
sys.path.append('/Users/devin/work/trident')
sys.path.append('/Users/devin/work/ext-plan-pydent')

import pydent
from pydent import AqSession, models
from pydent.models import Plan, Sample

# from aq_classes import Cursor, AqDefaults
# from pup_plan.pup_plans import PupPlan
# from golden_gate_leg import GoldenGateLeg

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

op_type = session.OperationType.where({'name': "Assemble NEB Golden Gate"})[0]

print(str(op_type.cost_model))

pplan = session.Plan.where({'name': 'Puppeteer Test Plan'})[-1]

print(pplan.estimate_cost())
