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

from collections import defaultdict, OrderedDict
import cv2
from sys import exit

from config.common import bright_red, dark_gray, bright_green, amber, dark_green
from utils.Rectangle import Rectangle


class Label:
    def __init__(self, droplet, stand_off=2, contour_box_margin=5, leading=2):
        """
        Initialize label.

        """

        # Droplet info for this label, for convenience.
        self.id = droplet.id  # Droplet id doubles as id for this label.
        self.initial_id = droplet.initial_id
        self.area = droplet.area
        self.contour = droplet.contour
        self.frame_number = droplet.frame

        # Distance between actual contour bounding box and the outline we display
        self.contour_box_margin = contour_box_margin
        # Distance between the displayed contour bounding box and text bounding boxes.
        self.stand_off = stand_off
        # Type line leading.
        self.leading = leading

        # Center of the label areas, used to compute distances between labeled items.
        # This is potentially slightly different from the centroid of the underlying
        # droplet, as the droplet centroid skews slightly based on the shape of the
        # droplet. (And this level of precision probably won't ever matter. But it's
        # easy to do. :)
        self.center = None

        # The four text Rectangles, 0-3, which can be used for labeling.
        # These can be compared directly to rectangles on other droplets
        # to gauge collisions between label areas.
        self.text_bounding_box = OrderedDict()

        # The status of each of the four possible text locations.
        # None if unknown, False if not available, True if available.
        self.corner_status = OrderedDict()
        for corner in [0, 1, 2, 3]:
            self.corner_status[corner] = None

        # Corner label area used to draw label, None or one of 0-3.
        self.corner_used = None

        # Private

        # The corners of the bounding box outline we display.
        self._contour_bounding_box_corners = None

        # Calculated text metrics for each line of text in a label
        self._text_data = defaultdict(dict)

        # The corner points nearest the contour of the four text areas.
        self._corner_points = {}

        # Dimensions of label text box.
        self._text_box_width = None
        self._text_box_height = None

        # Set-up

        self._calculate_bounding_box()
        self._calc_points()
        self._calc_center()

        def _repr_(self):

            if self.initial_id != self.id:
                initial_id_string = " (Was droplet {}.)".format(self.initial_id)
            else:
                initial_id_string = ""

            return "Label for droplet {}.{}".format(str(self.id), initial_id_string)

    ###
    def draw_contour_bounding_box(self, video_frame, color=bright_red, thickness=1):

        cv2.rectangle(
            video_frame, *self._contour_bounding_box_corners, color=color, thickness=1
        )

        return video_frame

    def _calculate_bounding_box(self):

        box_x, box_y, box_w, box_h = cv2.boundingRect(self.contour)
        box_point_1 = tuple([box_x - self.stand_off, box_y - self.stand_off])
        box_point_2 = tuple(
            [box_x + box_w + self.stand_off, box_y + box_h + self.stand_off]
        )

        self._contour_bounding_box_corners = (box_point_1, box_point_2)

    def _calc_points(self):

        # Text sizes. This is painful, as convincing opencv to do pixel-accurate text
        # is icky. Breaking this into smaller pieces would be good, but going to PIL
        # or Cairo/qahirah text would be better.

        # (This is evolving - I added a Rectangle class to help understand overlaps
        # between labels, and I'll back into using it here.)

        # initial id
        text_string = str(self.initial_id)
        (
            (
                self._text_data["width"]["initial_id"],
                self._text_data["height"]["initial_id"],
            ),
            self._text_data["baseline"]["initial_id"],
        ) = cv2.getTextSize(text_string, cv2.FONT_HERSHEY_PLAIN, 1, 1)
        self._text_data["height"][
            "initial_id"
        ] += 1  # fudge, as opencv reports height as one pixel less than it is
        self._text_data["baseline"][
            "initial_id"
        ] -= 1  # fudge, baseline seems consistently 1 px big

        # id
        text_string = str(self.id)
        (
            (self._text_data["width"]["id"], self._text_data["height"]["id"]),
            self._text_data["baseline"]["id"],
        ) = cv2.getTextSize(text_string, cv2.FONT_HERSHEY_PLAIN, 2, 1)
        self._text_data["height"]["id"] += 1
        self._text_data["baseline"][
            "id"
        ] -= 1  # fudge, baseline seems consistently 1 px big

        # area in pixels as "Npx"
        text_string = "{}px".format(self.area)
        (
            (self._text_data["width"]["area"], self._text_data["height"]["area"]),
            self._text_data["baseline"]["area"],
        ) = cv2.getTextSize(text_string, cv2.FONT_HERSHEY_PLAIN, 1, 1)
        self._text_data["height"]["area"] += 1
        self._text_data["baseline"][
            "area"
        ] -= 1  # fudge, baseline seems consistently 1 px big

        [self._text_box_width] = max(
            [self._text_data["width"][x]] for x in self._text_data["width"]
        )
        self._text_box_height = (
            self._text_data["height"]["id"]
            + self.leading
            + self._text_data["baseline"]["area"]
            + self.leading
            + self._text_data["height"]["area"]
        )

        if self.initial_id != self.id:
            self._text_box_height += self._text_data["height"]["initial_id"] + 1

        # Bounding box corner points.

        # These are the corner points on drawn contour bounding box, plus a stand-off
        # distance, and from which the label bounding boxes can be drawn.

        ((x1, y1), (x2, y2)) = self._contour_bounding_box_corners

        # 0th point is upper left, and then clockwise from there through 1, 2, and 3
        self._corner_points[0] = (x1 - self.stand_off, y1 - self.stand_off)
        self._corner_points[1] = (x2 + self.stand_off, y1 - self.stand_off)
        self._corner_points[2] = (x2 + self.stand_off, y2 + self.stand_off)
        self._corner_points[3] = (x1 - self.stand_off, y2 + self.stand_off)

        # And the actual label text area bounding boxes.

        self.text_bounding_box[0] = Rectangle(
            (
                self._corner_points[0][0] - self._text_box_width,
                self._corner_points[0][1] - self._text_box_height,
            ),
            self._corner_points[0],
        )

        self.text_bounding_box[1] = Rectangle(
            (
                self._corner_points[1][0],
                self._corner_points[1][1] - self._text_box_height,
            ),
            (
                self._corner_points[1][0] + self._text_box_width,
                self._corner_points[1][1],
            ),
        )

        self.text_bounding_box[2] = Rectangle(
            self._corner_points[2],
            (
                self._corner_points[2][0] + self._text_box_width,
                self._corner_points[2][1] + self._text_box_height,
            ),
        )

        self.text_bounding_box[3] = Rectangle(
            (
                self._corner_points[3][0] - self._text_box_width,
                self._corner_points[3][1],
            ),
            (
                self._corner_points[3][0],
                self._corner_points[3][1] + self._text_box_height,
            ),
        )

        # print(self.text_bounding_box)
        # print()

    def _calc_center(self):
        self.center = Rectangle(
            self.text_bounding_box[0].upper_left, self.text_bounding_box[2].lower_right
        ).center

    def draw_corner_box(self, video_frame, corner, color=dark_gray, thickness=1):
        """
        Draw one label bounding box. Routine to visualize corner box for debugging.

        :param video_frame: opencv video frame to draw on
        :param corner: corner number from 0, 1, 2, 3
        :param color: opencv BGR color tuplet
        :param thickness: line thickness in pixels

        """
        self.text_bounding_box[corner].draw(video_frame)

    def draw_all_corner_boxes(self, video_frame, color=dark_gray, thickness=1):
        """
        Draw all four label bounding boxes, also for debugging.

        :param video_frame: opencv video frame to draw on
        :param color: opencv BGR color tuplet
        :param thickness: line thickness in pixels

        """
        for corner in self.text_bounding_box:
            self.text_bounding_box[corner].draw(
                video_frame, color=dark_gray, thickness=1
            )

    def draw_label(self, video_frame, corner):

        # (And even more painful; doing the detail math.)

        # Corners are 0, 1, 2, 3; starting with 0 in upper left and proceeding clockwise.

        # Calculate the text origin coordinates for each of the three lines of text
        # (id, pixel area and initial id) for each text quadrant.

        # Occasional integer tweaks adjust inter-line spacing (y dimension) to make
        # line spacing appear the same when the order of lines is reversed.

        if corner == 0:
            droplet_id_xy = (
                self.text_bounding_box[0].upper_left[0]
                + (self._text_box_width - self._text_data["width"]["id"]),
                self.text_bounding_box[0].lower_right[1],
            )

            droplet_area_xy = tuple(
                [
                    self.text_bounding_box[0].upper_left[0]
                    + (self._text_box_width - self._text_data["width"]["area"]),
                    self.text_bounding_box[0].lower_right[1]
                    - self._text_data["height"]["id"]
                    - self._text_data["baseline"]["area"]
                    - self.leading,
                ]
            )

            droplet_initial_id_xy = tuple(
                [
                    self.text_bounding_box[0].upper_left[0]
                    + (self._text_box_width - self._text_data["width"]["initial_id"]),
                    self.text_bounding_box[0].lower_right[1]
                    - self._text_data["height"]["id"]
                    - self._text_data["baseline"]["area"]
                    - self.leading
                    - self._text_data["height"]["area"]
                    - self.leading
                    - 1,
                ]
            )
        elif corner == 1:
            droplet_id_xy = (
                self.text_bounding_box[1].upper_left[0],
                self.text_bounding_box[1].lower_right[1],
            )

            droplet_area_xy = tuple(
                [
                    self.text_bounding_box[1].upper_left[0],
                    self.text_bounding_box[1].lower_right[1]
                    - self._text_data["height"]["id"]
                    - self._text_data["baseline"]["area"]
                    - self.leading,
                ]
            )

            droplet_initial_id_xy = tuple(
                [
                    self.text_bounding_box[1].upper_left[0],
                    self.text_bounding_box[1].lower_right[1]
                    - self._text_data["height"]["id"]
                    - self._text_data["baseline"]["area"]
                    - self.leading
                    - self._text_data["height"]["area"]
                    - self.leading
                    - 1,
                ]
            )
        elif corner == 2:
            droplet_id_xy = (
                self.text_bounding_box[2].upper_left[0],
                self.text_bounding_box[2].upper_left[1]
                + self._text_data["height"]["id"],
            )

            droplet_area_xy = tuple(
                [
                    self.text_bounding_box[2].upper_left[0],
                    self.text_bounding_box[2].upper_left[1]
                    + self._text_data["height"]["id"]
                    + self._text_data["baseline"]["area"]
                    + self._text_data["height"]["area"]
                    + self.leading
                    - 2,
                ]
            )

            droplet_initial_id_xy = tuple(
                [
                    self.text_bounding_box[2].upper_left[0],
                    self.text_bounding_box[2].upper_left[1]
                    + self._text_data["height"]["id"]
                    + self._text_data["baseline"]["area"]
                    + self._text_data["height"]["area"]
                    + self.leading
                    + self._text_data["height"]["initial_id"]
                    + self.leading
                    + 1,
                ]
            )

        elif corner == 3:
            droplet_id_xy = (
                self.text_bounding_box[3].upper_left[0]
                + (self._text_box_width - self._text_data["width"]["id"]),
                self.text_bounding_box[3].upper_left[1]
                + self._text_data["height"]["id"],
            )

            droplet_area_xy = tuple(
                [
                    self.text_bounding_box[3].upper_left[0]
                    + (self._text_box_width - self._text_data["width"]["area"]),
                    self.text_bounding_box[3].upper_left[1]
                    + self._text_data["height"]["id"]
                    + self._text_data["baseline"]["area"]
                    + self._text_data["height"]["area"]
                    + self.leading
                    - 2,
                ]
            )

            droplet_initial_id_xy = tuple(
                [
                    self.text_bounding_box[3].upper_left[0]
                    + (self._text_box_width - self._text_data["width"]["initial_id"]),
                    self.text_bounding_box[3].upper_left[1]
                    + self._text_data["height"]["id"]
                    + self._text_data["baseline"]["area"]
                    + self._text_data["height"]["area"]
                    + self.leading
                    + self._text_data["height"]["initial_id"]
                    + self.leading
                    + 1,
                ]
            )
        else:
            exit("Corner not correct: {}, frame {}.".format(corner, self.frame_number))

        # And finally, draw some text.

        # Label id
        text_string = str(self.id)
        cv2.putText(
            video_frame,
            text_string,
            droplet_id_xy,
            fontFace=cv2.FONT_HERSHEY_PLAIN,
            fontScale=2,
            thickness=1,
            color=bright_green,
        )
        # Label pixel area
        text_string = "{}px".format(str(self.area))
        cv2.putText(
            video_frame,
            text_string,
            droplet_area_xy,
            fontFace=cv2.FONT_HERSHEY_PLAIN,
            fontScale=1,
            thickness=1,
            color=dark_green,
        )
        # Label initial id, if this droplet is a generation of an earlier one.
        if self.initial_id != self.id:
            text_string = str(self.initial_id)
            cv2.putText(
                video_frame,
                text_string,
                droplet_initial_id_xy,
                fontFace=cv2.FONT_HERSHEY_PLAIN,
                fontScale=1,
                thickness=1,
                color=amber,
            )

        # cv2.imwrite('./saved_video_frame.png', video_frame)

        return video_frame
