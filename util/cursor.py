# TODO: Fix this so that it can deal with fractional increments.
class Cursor:
    """
    `Cursor` is a class to keep track of where to put the next operation 
    in the graphical planner inerface of Aquarium. It uses appropriately 
    sized increments in `x` and `y` to help create a pretty layout.
    """
    def __init__(self, x=None, y=None):
        x = x or 1
        y = y or 10

        self.x_incr = 192
        self.y_incr = 64

        self.set_x(x, update=False)
        self.set_y(y, update=False)

        self.x_home = self.x
        self.max_x = self.x
        self.min_x = self.x

        self.y_home = self.y
        self.max_y = self.y
        self.min_y = self.y

    def set_x(self, x, update=True):
        self.x = round(x * self.x_incr)
        if update: self.update_max_min_x()

    def set_y(self, y, update=True):
        self.y = round(y * self.y_incr)
        if update: self.update_max_min_y()

    def set_xy(self, x, y, update=True):
        self.set_x(x, update)
        self.set_y(y, update)
        if update: self.update_max_min()

    def incr_x(self, mult=1):
        self.x += round(mult * self.x_incr)
        self.update_max_x()

    def decr_x(self, mult=1):
        self.x -= round(mult * self.x_incr)
        self.update_min_x()

    def incr_y(self, mult=1):
        self.y += round(mult * self.y_incr)
        self.update_max_y()

    def decr_y(self, mult=1):
        self.y -= round(mult * self.y_incr)
        self.update_min_y()

    def set_x_home(self, x=None):
        if x:
            self.x_home = round(x * self.x_incr)
        else:
            self.x_home = self.x

    def return_x(self):
        self.x = self.x_home

    def set_y_home(self, y=None):
        if y:
            self.y_home = round(y * self.y_incr)
        else:
            self.y_home = self.y

    def return_y(self):
        self.y = self.y_home

    def set_home(self):
        self.set_x_home()
        self.set_y_home()

    def return_xy(self):
        self.return_x()
        self.return_y()

    def update_max_x(self):
        if self.x > self.max_x:
            self.max_x = self.x

    def update_min_x(self):
        if self.x < self.min_x:
            self.min_x = self.x

    def update_max_y(self):
        if self.y > self.max_y:
            self.max_y = self.y

    def update_min_y(self):
        if self.y < self.min_y:
            self.min_y = self.y

    def update_max_min_x(self):
        self.update_max_x()
        self.update_min_x()

    def update_max_min_y(self):
        self.update_max_y()
        self.update_min_y()

    def update_max_min(self):
        self.update_max_min_x()
        self.update_max_min_y()

    def get_xy(self):
        return [self.x, self.y]

    def advance_to_next_step(self):
        self.set_xy(round(self.min_x / self.x_incr), round(self.min_y / self.y_incr))
        self.decr_y()
        self.set_home()
