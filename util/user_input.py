from datetime import datetime, timedelta
import json
import os

def get_input(plan_path=True, start_date=True, aq_instance=True):
    inputs = {}

    if plan_path: inputs["plan_path"] = get_plan_path()
    if start_date: inputs["start_date"] = get_start_date()
    if aq_instance:
        dirname = os.path.dirname(__file__)
        filename = os.path.join(dirname, 'secrets.json')
        with open(filename) as f:
            secrets = json.load(f)

        aq_instance_choices = list(secrets.keys())
        inputs["aq_instance"] = get_aq_instance(aq_instance_choices)

    print()

    return inputs

def get_aq_instance(aq_instance_choices):
    while True:
        print()
        print("Which Aquarium instance would you like to push to?")
        instance = input("{}: ".format(aq_instance_choices)).lower()

        if instance in aq_instance_choices:
            break

        else:
            print()
            print("I don't recognize '%s'. Try again." % instance)

    return instance

def get_start_date():
    while True:
        print()
        print("Enter the day you want to start the experiment.")
        print("The date must be on a Friday.")
        print("If you don't enter anything, the plan will be scheduled as soon as possible.")
        today = input("Start date (MM/DD/YY): ")

        if not today:
            today = datetime.today()
            break

        today = datetime.strptime(today, '%m/%d/%y')
        if today.weekday() == 4:
            break

        else:
            print()
            print("You entered a value that is not on a Friday. Try again.")

    dow = today.weekday()

    if dow <= 4:
        delay = timedelta(days=(4 - dow))
    else:
        delay = timedelta(days=(11 - dow))

    start_date = today + delay

    print("\nPlanning experiment to start on " + start_date.strftime('%m/%d/%y'))

    return start_date

def get_plan_path():
    print()
    print("Please provide a path to a folder containing the .json files for this plan.")
    plan_path = input("Path: ") 
    return plan_path