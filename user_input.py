from datetime import datetime, timedelta

def get_input():
    inputs = {}

    inputs["aq_plan_name"] = get_aq_plan_name()
    inputs["start_date"] = get_start_date()
    inputs["aq_instance"] = get_aq_instance()
    print()

    return inputs

def get_aq_instance():
    while True:
        print()
        print("Which Aquarium instance would you like to push to?")
        instance = input("Enter nursery or production: ").lower()

        if instance in ["nursery", "production"]:
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

def get_aq_plan_name():
    print()
    print("Please provide a name for this plan.")
    print("The name must match the name of a folder in the `plans` subdirectory.")
    aq_plan_name = input("Name: ")
    return aq_plan_name