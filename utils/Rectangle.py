import cv2

from config.common import bright_red

# Based on https://codereview.stackexchange.com/questions/151309/check-if-two-rectangles-overlap


class Rectangle:
    def __init__(self, upper_left=(0, 0), lower_right=(0, 0)):
        self.min_x = upper_left[0]
        self.max_x = lower_right[0]
        self.min_y = upper_left[1]
        self.max_y = lower_right[1]

    def intersects(self, other):
        if self.min_x > other.max_x or self.max_x < other.min_x:
            return False
        if self.min_y > other.max_y or self.max_y < other.min_y:
            return False
        return True

    def outside(self, other):
        if self.min_x < other.min_x or self.max_x > other.max_x:
            return True
        if self.min_y < other.min_y or self.max_y > other.max_y:
            return True
        return False

    def __and__(self, other):
        if not self.intersects(other):
            return Rectangle()
        min_x = max(self.min_x, other.min_x)
        max_x = min(self.max_x, other.max_x)
        min_y = max(self.min_y, other.min_y)
        max_y = min(self.max_y, other.max_y)
        return Rectangle((min_x, min_y), (max_x, max_y))

    intersect = __and__

    def __or__(self, other):
        min_x = min(self.min_x, other.min_x)
        max_x = max(self.max_x, other.max_x)
        min_y = min(self.min_y, other.min_y)
        max_y = max(self.max_y, other.max_y)
        return Rectangle((min_x, min_y), (max_x, max_y))

    union = __or__

    def __str__(self):
        return "Rectangle(({self.min_x}, {self.min_y}), ({self.max_x}, {self.max_y})   )".format(
            self=self
        )

    def draw(self, video_frame, color=bright_red, thickness=1):
        cv2.rectangle(
            video_frame,
            (self.min_x, self.min_y),
            (self.max_x, self.max_y),
            color=color,
            thickness=1,
        )

    # These could all be computed in __init__. The only reason
    # to have them as properties is if the Rectangle might have its
    # dimensions changed after it's created.

    @property
    def area(self):
        return (self.max_x - self.min_x) * (self.max_y - self.min_y)

    @property
    def center(self):
        return (
            ((self.max_x - self.min_x) / 2) + self.min_x,
            ((self.max_y - self.min_y) / 2) + self.min_y,
        )

    @property
    def upper_left(self):
        return (self.min_x, self.min_y)

    @property
    def lower_right(self):
        return (self.max_x, self.max_y)
