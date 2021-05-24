YELLOW = "\033[93m"
BLUE = "\033[94m"
RED = "\033[91m"
CLEAR = "\033[0m"

def print_yellow(msg):
    print("{}{}{}".format(YELLOW, msg, CLEAR))

def print_red(msg):
    print("{}{}{}".format(RED, msg, CLEAR))

def print_blue(msg):
    print("{}{}{}".format(BLUE, msg, CLEAR))

def warn(msg):
    """Prints WARNING statement to stdout in yellow"""
    print_yellow("WARNING: {}".format(msg))