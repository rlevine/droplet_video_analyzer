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

from collections import defaultdict
from math import trunc
import cv2

"""

Found droplets, from our initial scan, are numbered consecutively for the entire
video sequence, from class variable master_count. Each found contour receives a unique 
ID, which will survive in the droplet data as self.initial_id, even if we subsequently 
discover they're views of another droplet.

If a droplet is tracked and found to be an image of an already-captured droplet, the 
contour, centroid, pixel area and ID info, etc. are added to the data list for the 
previously captured droplet.

droplets = OrderedDict()
droplets[id] = self._data[0]

droplet_data = {
                'contour': contour,
                'centroid': centroid,
                'area': area,
                'frame': frame
                'id': id,
                'initial_id': id
                }

The most recent droplet data is always in list self._data in the 0th position.

self._data.insert(0,droplet_data)

method self.relocate(), given a more recent droplet, will push a new
droplet_data dict onto the list at [0].

self.generations() returns the number of data versions for a given droplet.

self.contour_history() returns a list of contours from the set of generations,
from most recent to oldest.

"""


class Droplet:

    master_count = 1  # Class data counter for creating new ids.

    # # Master class indices for droplet info.
    #
    # # Returns a droplet.
    # index_by_droplet = {}
    # # Returns a list of frame numbers.
    # index_by_frame = defaultdict(list)
    # # Returns a list of droplets with key (int) number of pixels.
    # index_by_area = defaultdict(list)

    def __init__(self, contour=None):
        """
        Initialize droplet.

        :param contour: np contour array

        """
        self.id = Droplet.master_count  # id for this droplet
        self._data = []  # The data for this droplet; current is always in data[0]

        # Initialize blank data.
        droplet_data = {
            "contour": None,
            "centroid": None,
            "area": None,
            "frame": None,
            "initial_id": self.id,
            "id": self.id,
        }

        self._data.append(droplet_data)

        Droplet.master_count += 1

    @property
    def contour(self):
        return self._data[0]["contour"]

    @contour.setter
    def contour(self, contour):
        self._data[0]["contour"] = contour
        self.centroid = contour

    @property
    def centroid(self):
        return self._data[0]["centroid"]

    @centroid.setter
    def centroid(self, contour):
        self._data[0]["centroid"] = self._calc_centroid(contour)

    @property
    def area(self):
        return self._data[0]["area"]

    @area.setter
    def area(self, area):
        self._data[0]["area"] = area

    @property
    def frame(self):
        return self._data[0]["frame"]

    @frame.setter
    def frame(self, frame):
        self._data[0]["frame"] = frame

    @property
    def initial_id(self):
        return self._data[0]["initial_id"]

    ###

    def relocate(self, destination_droplet):
        """
        Add a new set of location data to this droplet.

        :param droplet at new location:
        """

        new_droplet_data = {
            "contour": destination_droplet.contour,
            "centroid": destination_droplet.centroid,
            "area": destination_droplet.area,
            "frame": destination_droplet.frame,
            # initial_id is the one it was created with.
            "initial_id": destination_droplet.initial_id,
            # id is the id of the original droplet, of which it's a repeat sighting.
            "id": self.id,
        }

        self._data.insert(0, new_droplet_data)

    ###
    def generations(self):
        """
        Returns number of location generations for a droplet.

        :return: integer generation count.
        """
        return len(self._data)

    def contour_history(self):
        """
        Return contours from all locations of a droplet.

        :return: List of contour arrays.
        """
        # contours = [self.contour[x]['contour'] for x in range(len(self._data))]
        # return contours
        return [list(self._data[x]["contour"]) for x in range(len(self._data))]

    # def create_indices(self):
    #     """
    #     Create index entries for droplet.
    #     """
    #     Droplet.index_by_frame[self.frame].append(self.id)
    #     Droplet.index_by_droplet[self.id] = self
    #     Droplet.index_by_area[trunc(self.area)].append(self.id)

    def _calc_centroid(self, contour):

        # Get the center of the droplet by calculating its moments.
        m = cv2.moments(contour)
        if m["m00"] != 0:
            centroid = tuple([m["m10"] / m["m00"], m["m01"] / m["m00"]])
        else:
            # m00 is 0 when there are too few points in the1
            # contour (ie the contour is a single pixel or a line with no interior)
            # so just take an average of the points we do have.
            centroid = tuple([sum(x) / len(x) for x in zip(*contour)][0])

            # print("m00 == 0! - {} point{}".format(len(contour), ess(len(contour))))  # debug
            # print(
            #     "non-moment center = {}, {}".format(
            #         raw_centroids[i][0], raw_centroids[i][1]
            #     )
            # )  # debug

        return centroid
