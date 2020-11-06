# Copyright (c) 2020 Fredrick Levine
# rick@xoab.us
#
# This file is part of Droplet Video Analyzer
# https://github.com/rlevine/droplet_video_analyzer
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; version 2.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.

###

import re
import sys
from math import copysign
from math import log10
from math import radians
from math import sin
from math import cos
from math import degrees
from math import atan2
from math import pi
import numpy as np
from itertools import islice
from collections import OrderedDict


#
# general utility functions
#


def log_transform(number):
    """
    Perform a log transform on the supplied number. I'm returning 999 instead of NaN
    for zeroes, as I'm catching out-of-range vales with an array mask on the output side.

    :param number: int or float
    :return: transformed value
    """
    if number != 0:
        return -1 * copysign(1.0, number) * log10(abs(number))
    else:
        # return np.nan
        return 999


def ess(count, ending="s"):
    """
    Return 's' or 'es' to add plural to words.
    :param count: integer to be described
    "param ending" either 'es' or assumed to be 's'
    :return: 's' or 'es' or ''
    """
    if count == 1:
        return ""
    else:
        if ending == "es":
            return "es"
        else:
            return "s"


def vector(from_tuple, to_tuple, reverse_xy=False):
    """
    Returns tuple of directional vector between two points.

    :param from_tuple:
    :param to_tuple:
    :return: tuple
    """

    coords = [n - m for m, n in zip(from_tuple, to_tuple)]
    # coords[1] = -coords[1]

    if reverse_xy:
        coords = coords[::-1]

    return tuple(coords)


def bearing_angle(point_a, point_b):
    """
    Calculate the 360-degree clockwise bearing angle between two cartesian points.

    Flips y coordinate math for reversed (increasing downwards) y axis.

    :param point_a: tuple xy coordinates
    :param point_b: tuple xy coordinates
    :return: float angle in degrees
    """
    radians = np.arctan2(point_b[0] - point_a[0], point_a[1] - point_b[1])
    return np.rad2deg((radians) % (2 * np.pi))


def average_angles(angles):
    """
    Calculate the average of a list of angles.

    Weeds out None value_1_values, allowing it to be used where some value_1_values may be missing.

    Adapted from this: https://stackoverflow.com/a/25579022/1705128

    :param angles: list of angles in degrees
    :return: angle in degrees rounded to two decimals
    """

    filtered_angles = [x for x in angles if x is not None]

    sin_sum = 0
    cos_sum = 0
    angle_count = len(filtered_angles)

    if not angle_count:
        return None

    for angle in filtered_angles:

        angle_in_radians = angle * (pi / 180)

        sin_sum += sin(angle_in_radians)
        cos_sum += cos(angle_in_radians)

    average_in_radians = atan2(sin_sum / angle_count, cos_sum / angle_count)
    average_in_degrees = average_in_radians * (180 / pi)

    if average_in_degrees < 0:
        average_in_degrees += 360

    if average_in_degrees == 360:
        return 0.0

    return round(average_in_degrees, 2)


def reverse_angle(angle):

    return (angle + 180) % 360


def andbytes(abytes, bbytes):
    """
    # & two bytestrings. For some reason, python doesn't implement this.
    # I've read that it might be because it wouldn't make sense for other list-like
    # constructs, and they didn't implement it for the sake of paradigm consistency.
    # That feels like a foolish consistency given something that seems so obvious.
    # (But being able to treat a bytestring like a list is pretty cool. :)

    :param abytes: bytestring
    :param bbytes: bytestring
    :return: boolean
    """

    return bytes([a & b for a, b in zip(abytes, bbytes)])

    # return bytes(map(lambda a,b: a & b, abytes, bbytes))
    # will work, too, Is it more or less readable? :)


###
# strip_tokens(<target_string>)
#
# Removes all unused substitution tokens from a string.
#


def strip_tokens(target_string):

    target_string = re.sub(r"(?m)%%.*?%%", "", target_string)

    return target_string


###
# substitute_tokens(<token_dict>, <target_string>)
#
# Given a dictionary with token/replacement pairs, replaces all tokens in the target string
# (delimited as %%token_name%%) with the replacement text. We'll ignore undefined replacement value_1_values,
# and convert all value_1_values to strings.
#


def substitute_tokens(token_dict, target_string):

    # We dupe the token keys so we run through the list twice.
    # Some of the inserted text may itself contain tokens, and the
    # second pass will catch them.
    tokens = list(token_dict.keys()) * 2

    for token in tokens:
        if str(token_dict[token] != ""):  # Don't sub if blank.
            target_string = re.sub(
                r"(?im)%%{0}%%".format(token), str(token_dict[token]), target_string
            )

    # remove any leftover tokens
    target_string = strip_tokens(target_string)

    return target_string


# Simple ANSI escape color print routines.

# pretty - A miniature library that provides a Python print and stdout
# wrapper that makes colored terminal text easier to use (eg. without
# having to mess around with ANSI escape sequences). This code is public
# domain - there is no license except that you must leave this header.
#
# Copyright (C) 2008 Brian Nez <thedude at bri1 dot com>
#

# fmt: off
codeCodes = {
    'black':     '0;30',   'bright gray':   '0;37',
    'blue':      '0;34',   'white':         '1;37',
    'green':     '0;32',   'bright blue':   '1;34',
    'cyan':      '0;36',   'bright green':  '1;32',
    'red':       '0;31',   'bright cyan':   '1;36',
    'purple':    '0;35',   'bright red':    '1;31',
    'yellow':    '0;33',   'bright purple': '1;35',
    'dark gray': '1;30',   'bright yellow': '1;33',
    'normal':    '0'
}
# fmt: on


def printc(text, color, end="\n"):
    """Print in color."""
    print("\033[" + codeCodes[color] + "m" + text + "\033[0m", end=end)


def writec(text, color):
    """Write to stdout in color."""
    sys.stdout.write("\033[" + codeCodes[color] + "m" + text + "\033[0m")


def switchColor(color):
    """Switch console color."""
    sys.stdout.write("\033[" + codeCodes[color] + "m")


if __name__ == "__main__":
    print("Welcome to the test routine!")
    print("I will now try to print a line of text in each color.")
    for color in codeCodes.keys():
        writec("Hello, world!", color)
        print("\t", color)

# Rick: ... a few added funcs so I can use this with other prints...


def start_color(color):
    return "\033[" + codeCodes[color] + "m"


def stop_color():
    return "\033[0m"
