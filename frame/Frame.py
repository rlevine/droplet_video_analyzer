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

from math import trunc
from collections import OrderedDict
from droplet.Droplet import Droplet


class Frame:
    def __init__(self, id):
        """
        Initialize video frame.

        :return: int sequence number of frame
        """
        self.id = id
        self.timecode = frames2timecode(self.id)

        self._droplets = OrderedDict()

    @property
    def droplets(self):
        return self._droplets

    @property
    def droplet_count(self):
        return len(self._droplets)

    def add_droplet(self):
        """
        Add new droplet to the video frame.

        :param droplet_id:
        """
        d = Droplet()
        self._droplets[d.id] = d

        return d

    def remove_droplet(self, droplet_id):
        """
        Remove a droplet from the video frame.

        :param droplet_id:
        """

        self._droplets.remove(droplet_id)


###
# frames2timecode(<frame count>, <frame_rate>, <drop frame flag>)
#
# Converts a supplied frame count to a colon-separated string representing the
# corresponding time code. Drop frame math isn't implemented. :)


def frames2timecode(frame_count, rate=30, drop=False):
    """
    Converts a supplied frame count to a colon-separated string representing the
    corresponding time code. Drop frame math isn't implemented. :)

    :param frame_count: int total number of frames
    :param rate: frames per second, default is 30
    :param drop: :) only non-drop
    :return: colon-separated timecode string
    """
    frames_per_hour = rate * 60 * 60
    frames_per_minute = rate * 60
    hours = trunc(frame_count / frames_per_hour)
    minutes = trunc(frame_count / frames_per_minute) % 60
    seconds = trunc((frame_count % frames_per_minute) / rate)
    frames = (frame_count % frames_per_minute) % rate

    return "{:02d}:{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds, frames)


def find_droplets(frame):
    pass
