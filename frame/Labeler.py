from collections import OrderedDict
from itertools import combinations
from itertools import product
from itertools import islice
from scipy.spatial import distance
from math import atan2
from math import pi
import numpy as np
import cv2

from config.common import bright_red
from frame.Label import Label
from utils.common import printc
from utils.common import andbytes
from utils.common import start_color
from utils.common import stop_color
from utils.common import vector
from utils.common import bearing_angle
from utils.common import average_angles
from utils.common import reverse_angle
from utils.Rectangle import Rectangle


class Labeler:
    def __init__(self, frame_count, frame_shape=None, VERBOSE=False, DEBUG=False):
        """
        Initialize droplet labeler for a video frame.

        """
        self._labels = OrderedDict()
        self.frame = frame_count
        self._VERBOSE = VERBOSE
        self._DEBUG = DEBUG
        self.frame_edge = 5
        self._video_frame_safe_boundary = self._calc_video_frame_safe_boundary(
            frame_shape
        )
        self.video_frame_boundary = Rectangle((0, 0), frame_shape)

        # Pixel buffer width at the edge of the video frame to avoid putting labels in.

    # @property
    # def video_frame(self):
    #     return self.video_frame
    # @video_frame.setter
    # def video_frame(self, frame):
    #     self.video_frame = frame

    @property
    def labels(self):
        return self._labels

    @property
    def label_count(self):
        return len(self._labels)

    def save(self):
        # For debugging, to make it easy to save the current video frame,
        cv2.imwrite("./saved_video_frame.png", self.video_frame)

    def add_label(self, droplet):
        """
        Add new label to the labeler.

        :param label_id:
        """
        label = Label(droplet, stand_off=2, contour_box_margin=5, leading=2)

        self._labels[label.id] = label

        return label

    def _calc_video_frame_safe_boundary(self, frame_shape):

        frame_width, frame_height = frame_shape
        # Video frame boundary minus the frame edge buffer.
        video_frame_safe_boundary = Rectangle(
            (0 + self.frame_edge, 0 + self.frame_edge),
            (frame_width - self.frame_edge, frame_height - self.frame_edge),
        )

        return video_frame_safe_boundary

    def _check_for_edge_closeness(self, video_frame):

        # Cycle through the four label area bounding boxes, and mark the corner status
        # False if that rectangle intersects the video frame boundary minus an offset.

        for label in self.labels:
            for box in range(4):
                if (
                    self.labels[label]
                    .text_bounding_box[box]
                    .outside(self._video_frame_safe_boundary)
                ):
                    self.labels[label].corner_status[box] = False

    def draw(self, video_frame):

        # Each droplet has four possible label positions, 0-3, starting in with the
        # upper left quadrant, and continuing clockwise. We'll need a data structure
        # for the label quadrants, to indicate if a quadrant cannot be considered or
        # is available for placement consideration. Possible quadrant states are:
        #
        #     - available for use
        #     - unavailable (for instance if it's too close to the edge of the frame)
        #     - used for the droplet's label
        #     - temporarily used in a fitting step, but can be reset back to unused
        #
        # 0. Check all labels to make sure none are being lost at frame edges.
        #    Mark label rects within a pixel margin (10px?) of a screen edge
        #    as unusable.

        #
        # Check for label too close to the edge of the video frame.
        #

        self._check_for_edge_closeness(video_frame)

        #
        # Find label collisions.
        #

        if len(self.labels) > 1:

            # If only one label in this frame, we've already checked proximity to the
            # frame edge, so skip.

            label_ids = sorted(list(self.labels))

            # This visualizes all the potential collisions between droplet labels.

            # Creates an array of all combinations of pairs droplets in this frame
            # and all possible combinations of the four label areas in a two-droplet
            # combination. It populates the array with the pixel area of any overlap
            # of each label area between each specific pair of droplets in the frame.

            # All droplets in pairs, without replacement. This is one triangle in a
            # combination matrix, without the identity diagonal.
            id_combinations = list(combinations(label_ids, 2))
            # All label corner area possibilities, with replacement and identities, as
            # we're comparing any possible combination of two independent sets of four.
            corner_combinations = list(product([0, 1, 2, 3], [0, 1, 2, 3]))
            label_overlaps = np.zeros(
                (len(id_combinations), len(corner_combinations)), dtype=np.int16
            )

            # Finds the area for each combination using the _and_ method
            # from Rectangle.
            for row_index, id_tuple in enumerate(id_combinations):
                for column_index, corner_tuple in enumerate(corner_combinations):
                    label_overlaps[row_index, column_index] = (
                        self.labels[id_tuple[0]].text_bounding_box[corner_tuple[0]]
                        & self.labels[id_tuple[1]].text_bounding_box[corner_tuple[1]]
                    ).area

            # Pretty-printing the resulting matrix.
            if self._DEBUG:
                printc(
                    "\nLabel overlaps for frame {}\n".format(str(self.frame + 1)),
                    "bright yellow",
                )
                header_string = "           {}".format(
                    " ".join(
                        [
                            " {}/{}".format(*corner_combinations[x])
                            for x in range(len(corner_combinations))
                        ]
                    )
                )
                printc(header_string, "red")

            for row_index, id_tuple in enumerate(id_combinations):
                if self._DEBUG:
                    printc(
                        "{:>4} {:>4}: ".format(id_tuple[0], id_tuple[1]), "red", end=""
                    )
                area_list = [
                    "{:>4}".format(label_overlaps[row_index][x])
                    for x in range(len(label_overlaps[row_index]))
                ]

                # TODO Some of this code, to identify and fix total overlaps between
                # TODO two droplets, might get moved to the "fix" section instead of here
                # TODO in "find."

                # The identity overlaps, ie area 1 with 1, 2 with 2, etc., happen when
                # a droplet is pretty much superimposed on another. Those combinations
                # are in spots 0, 5, 10 and 15 in our sorted list of keys. This uses a
                # boolean and on a byte string representing all possibilities that
                # overlap to find that condition, and sets the allowed label positions
                # to be diagonally opposite one another for the two  droplets. (And it
                # colors those numbers blue in the table to make them easy to see.)

                bit_status_string = andbytes(
                    b"1000010000100001",
                    b"".join(
                        [
                            b"0" if label_overlaps[row_index][x] == 0 else b"1"
                            for x in range(len(area_list))
                        ]
                    ),
                )
                if bit_status_string == b"1000010000100001":
                    area_list_string = " ".join(
                        [
                            start_color("bright blue") + area_list[x] + stop_color()
                            if b"1000010000100001"[x] == 49  # integer byte value
                            else area_list[x]
                            for x in range(len(bit_status_string))
                        ]
                    )

                    area_list_string = (
                        area_list_string
                        + start_color("bright red")
                        + " (complete overlap)"
                        + stop_color()
                    )

                    # These two labels have overlaps in all four of their corner areas.
                    # This gets the corners for the destination label of the vector,
                    # tuple[1].

                    # corners = self._pick_corners(
                    #     vector(
                    #         self.labels[id_tuple[0]].center,
                    #         self.labels[id_tuple[1]].center,
                    #     )
                    # )

                    # We're setting the corner or corners to avoid to False, so
                    # we'll get the reversed list.

                    # TODO Ignoring this for now, until we see if the distance
                    # TODO approach works to avoid collisions.
                    # for corner in self._reverse_corners(corners):
                    #     self.labels[id_tuple[0]].corner_status[corner] = False
                    # # And for the other label, avoid the original list.
                    # for corner in corners:
                    #     self.labels[id_tuple[1]].corner_status[corner] = False
                    #
                    # print("Overlapping labels: {} and {}.".format(*id_tuple)) # Debug

                else:
                    area_list_string = " ".join(area_list)

                # print(bit_status_string)
                if self._DEBUG:
                    print(area_list_string)
            if self._DEBUG:
                print()

            #
            # Fix label overlaps.
            #

            # if label_overlaps.sum() != 0:  # There are overlaps.

            if self.frame == 2:
                debug_Catcher = True

            # Debug - draw a red line connecting droplets
            if self._DEBUG:
                self._connect_dots(video_frame)

            # Pick a corner for the label, hopelfully one that won't
            # interfere with other droplets.
            self._choose_label_corners()

            if self._DEBUG:
                print()

        #
        # Make changes to and draw labels.
        #

        for label in self.labels:

            # if self.frame == 106:
            #     debug_catcher = True

            # Just to make it easier to type and read...
            this_label = self.labels[label]

            # If this label doesn't have a corner defined from any previous operations.
            if not this_label.corner_used:

                # Assign label corner, starting with 0, checking for any
                # marked as False by frame edge test or collision code, etc.
                for corner in this_label.corner_status:
                    if this_label.corner_status[corner] is not False:
                        this_label.corner_used = corner
                        break
                    else:
                        # Uh oh. No available corners. Force a corner
                        # and complain.
                        this_label.corner_used = 2
                        # printc("\n!!!\n!!! Label {} has no available corner!\n!!!"
                        # .format(this_label.id), 'bright red') # Debug

            # For debugging and manual experimentation.
            if self._DEBUG:
                this_label.draw_all_corner_boxes(video_frame)
            # video_frame = this_label.draw_label(video_frame, 0)
            # video_frame = this_label.draw_label(video_frame, 1)
            # video_frame = this_label.draw_label(video_frame, 2)
            # video_frame = this_label.draw_label(video_frame, 3)

            video_frame = this_label.draw_label(video_frame, this_label.corner_used)

        return video_frame

    def _choose_label_corners(self):
        # List of object centers
        object_centers = [self.labels[x].center for x in self.labels]
        # List of object ids in the same order as object_centers.
        object_indices = list(self.labels)

        # Sorted list of droplet ids, starting with droplet nearest
        # to the center of the frame, and continuing to the next nearest
        # droplet through all the droplets.
        object_list_by_distance = self._sort_nearest(
            [
                self.video_frame_boundary.center,
            ],
            object_centers,
            object_indices,
        )

        # Create a dict of all droplet center coords in this frame.
        object_dict = OrderedDict()
        object_dict = {x: self.labels[x].center for x in object_list_by_distance}

        ids = list(object_dict)

        # List of chained pairs of droplets, by distance.
        pairs = [(ids[x : x + 2]) for x in range(len(ids)) if x < len(ids) - 1]

        # Next, calculate the incoming and outgoing angles of the vectors
        # between each pair of droplet centers.
        in_angle = OrderedDict({x: None for x in ids})
        out_angle = OrderedDict({x: None for x in ids})

        # Calulate the gozinta and gozouta.
        for a, b in pairs:
            out_angle[a] = bearing_angle(self.labels[a].center, self.labels[b].center)
            # print(
            #     "{}\t{}\t{}\t{}\t{}\t{}\t{}".format(
            #         a, b, *self.labels[a].center, *self.labels[b].center, out_angle[a]
            #     )
            # )  # Debug

        for b, a in pairs:
            in_angle[a] = bearing_angle(self.labels[a].center, self.labels[b].center)
            # print(
            #     "{}\t{}\t{}\t{}\t{}\t{}\t{}".format(
            #         b, a, *self.labels[b].center, *self.labels[a].center, in_angle[a]
            #     )
            # )  # Debug
            # print()  # Debug

        for droplet_id in ids:
            # print(in_angle[droplet_id], out_angle[droplet_id])  # Debug.
            average_angle = average_angles(
                [in_angle[droplet_id], out_angle[droplet_id]]
            )
            reversed_angle = reverse_angle(average_angle)

            # Mark the appropriate corner to use for the label.

            corner_map = [1, 2, 3, 0]

            corner = corner_map[int(reversed_angle // 90)]

            # Check to see if the label corner has been marked off-limits
            # because the droplet is too close to the frame edge.
            if self.labels[droplet_id].corner_status[corner] is not False:
                # Good to go.
                self.labels[droplet_id].corner_used = corner
            else:
                # Cycle through the corners, and just pick another one.
                # (Labels near the frame edges usually aren't involved in pile-ups,
                # so this will rarely be a problem.)
                if self._DEBUG:
                    print(
                        "Found an edge collision: droplet {}, corner {}".format(
                            droplet_id, corner
                        )
                    )
                for corner_candidate in [0, 1, 2, 3]:
                    if (
                        self.labels[droplet_id].corner_status[corner_candidate]
                        is not False
                    ):
                        self.labels[droplet_id].corner_used = corner_candidate
                        break

    def _connect_dots(self, video_frame):
        # List of object centers
        object_centers = [self.labels[x].center for x in self.labels]
        # List of object ids in the same order as point_list.
        object_indices = list(self.labels)

        object_list_by_distance = self._sort_nearest(
            [
                self.video_frame_boundary.center,
            ],
            object_centers,
            object_indices,
        )

        # Included just for fun: connect the dots.
        # Draw a line from droplet to droplet, starting at the center
        # of the screen, and then to next nearest droplet.

        # Red cross at center of screen.

        [center_x, center_y] = [int(x) for x in self.video_frame_boundary.center]

        arm_length = 5
        x_up_left = (center_x - arm_length, center_y - arm_length)
        x_down_right = (center_x + arm_length, center_y + arm_length)
        x_down_left = (center_x - arm_length, center_y + arm_length)
        x_up_right = (center_x + arm_length, center_y - arm_length)
        video_frame = cv2.line(video_frame, x_up_left, x_down_right, bright_red, 1)
        video_frame = cv2.line(video_frame, x_down_left, x_up_right, bright_red, 1)

        # Connect the dots.
        label_line_points = [
            tuple([int(coord) for coord in self.labels[object].center])
            for object in object_list_by_distance
        ]
        x_of_line_points = [center_x] + [coord[0] for coord in label_line_points]
        y_of_line_points = [center_y] + [coord[1] for coord in label_line_points]
        start_points = list(zip(x_of_line_points, y_of_line_points))
        end_points = start_points[1:]

        for start_point, end_point in zip(start_points, end_points):
            video_frame = cv2.line(video_frame, start_point, end_point, bright_red, 1)

    def _angle(self, vector):

        y, x = vector
        radians = atan2(y, x)
        degrees = radians * (180 / pi)
        # if x > 0 and y < 0:
        #     degrees += 90
        # elif x > 0 and y > 0:
        #     degrees = 90 - degrees
        # elif x < 0 and y < 0:
        #     degrees = 270 - degrees
        # elif x < 0 and y > 0:
        #     degrees += 270

        # if radians < 0:
        #     radians += 2 * pi
        # degrees = radians * (180 / pi)

        return degrees

    def _pick_corners(self, label_vector):
        """
        Given a vector tuple between two labels, FROM A TO B, return the one or
        two corner choices for the B label to use to avoid overlapping with the A label.

        :return: list with one or two integer value_1_values from 0-3
        """
        # fmt: off
        corner_choices = [(0, 1), (1,), (1,), (1,),
                          (1, 2), (2,), (2,), (2,),
                          (2, 3), (3,), (3,), (3,),
                          (3, 0), (0,), (0,), (0,)]
        # fmt: on

        degrees = self._angle(label_vector)
        index = round(degrees / (360.0 / len(corner_choices)))

        return corner_choices[index % len(corner_choices)]

    def _reverse_corners(self, corner_list):
        """
        Return diagonally opposite label corners given a list of corners.

        :param corner_list:
        :return: list
        """
        reverse_corner_map = [2, 3, 0, 1]
        return [reverse_corner_map[corner] for corner in corner_list]

    def _sort_nearest(
        self, first_point, object_centers, object_indices, last_found=None
    ):
        """
        Given a an x,y coordinate tuple for a starting point and a pair of lists, one of
        object center coordinates and the other identifiers for each center point, in
        corresponding order, finds the object nearest to the starting point and then
        recursively sorts the remainder of the object list into a chain, where each
        object is the one closest, by euclidean distance, to its predecessor. Returns
        the sorted list of object ids.

        :param first_point: starting x,y tuple; for instance, the center of video frame
        :param object_centers: list of object center coordinate tuples
        :param object_indices: list of object ids for the centers, in the same order
        :param last_found: internal tracker for intermediate recursion results

        """

        # last_found in use is a mutable list, and is created only once. If we leave
        # things in it, they'll come back to haunt us. So we default it as a param to
        # None, and start it up here.
        if last_found is None:
            last_found = []

        if len(object_indices) > 1:

            # Creates an array, with distances from the starting point to all objects.
            distances = distance.cdist(first_point, object_centers, "euclidean")

            # Finds index of object/coordinate pair with the shortest distance to
            # starting point.
            nearest_index = distances.argmin(axis=1)[0]

            # Removes that index from the main list and adds it to the intermediate
            # result list.
            last_found.append(object_indices.pop(nearest_index))
            # The corresponding coordinate pair becomes the new starting point.
            nearest_point = [
                object_centers.pop(nearest_index),
            ]

            # And we repeat, until our original list only has one object left.
            last_found = self._sort_nearest(
                nearest_point, object_centers, object_indices, last_found=last_found
            )
        else:
            # Add the remaining object id to the list.
            last_found.extend(object_indices)

        return last_found
