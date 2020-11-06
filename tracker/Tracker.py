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

from scipy.spatial import distance
from collections import OrderedDict
import cv2
import sys
import numpy as np
import re

from prettytable import PrettyTable
from droplet.Droplet import Droplet
from utils.common import printc, log_transform, start_color, stop_color

"""

Data structure for droplets in each frame is a list of simple dicts that
represent each droplet found in a frame:

    droplet_data = {
                    'contour': NP contour array
                    'centroid': (xy) float coordinate tuple
                    'area': integer area in pixels (Pixels are thresholded to bright
                            white, so there are no fractional value_1_values.)
                    'frame': video frame number from beginning of file, 0-based
                    'id': integer droplet count, assigned when contour is first found
                    'initial_id': the originally assigned droplet number,
                                  from the first raw scan
                    }

droplet_data[0] in the list is the most recent appearance of the droplet. When a droplet
is discovered to be a duplicate of a prior droplet, (using distance closeness or
shape similarity) a new droplet_data[0] is created, pushing right/down the prior data.
The frame number is the frame in which the current contour coordinates appeared, but
droplet id is set to be the id number first discovered: ie the frame number is where last
seen, but the id is the id of the parent. initial_id holds the original droplet id.

I'm not sure how best to handle varying droplet pixel area; for the first pass, I'm using
the initial pixel size, and not adjusting overall pixel count for duplicate
instances.

"""


class Tracker:
    def __init__(
        self,
        frames_before_deregister=10,
        distance_threshold=40,
        confidence_threshold=5.0,
        droplet_corrections={},
        droplet_master=None,
        BACK=False,
        VERBOSE=None,
    ):

        # Each registry is an OrderedDict of droplet data dicts, keyed by droplet id.
        self.current_droplet_registry = OrderedDict()
        self.droplet_candidate_registry = OrderedDict()
        self.droplet_history_registry = OrderedDict()

        # These are hardwired, rather than being a global config.
        self._SHOW_DROPLET_SUMMARY = True
        self._SHOW_DROPLET_TABLE = True

        self._droplet_corrections = droplet_corrections

        self._droplet_master = droplet_master

        # Ageing dict is keyed by droplet id, value number of frames seen since last
        # present in a frame.
        self._ageing = OrderedDict()

        # Dict for collecting droplet separation for duplicate droplets, to understand
        # thresholds.
        # self.distance_research = defaultdict(dict)

        self._VERBOSE = VERBOSE

        # Threshold value_1_values
        self._FRAMES_BEFORE_DEREGISTER = frames_before_deregister
        self._CONFIDENCE_THRESHOLD = confidence_threshold
        self._DISTANCE_THRESHOLD = distance_threshold

    def _register(self, droplet_dict):
        # The default flow is to register to current, copy to history, and
        # eventually deregister from history.
        self.current_droplet_registry[droplet_dict.id] = droplet_dict
        self._ageing[droplet_dict.id] = 0

    def _deregister(self, id):
        # Popping an unknown key from a list won't throw an exception,
        # but OrderedDict does. :(
        try:
            self.droplet_history_registry.pop(id)
        except KeyError:
            pass
        try:
            self._ageing.pop(id)
        except KeyError:
            pass

    def _deregister_current_housekeeping(self, id):
        # When we need to remove a droplet from current prematurely,
        # because it's a duplicate.
        self.current_droplet_registry.pop(id)
        self._ageing.pop(id)  # In case it made it to the history.

    def _copy_to_history(self, id):
        """
        Move droplet data dict from current set to history set.
        :param id: unique droplet id
        """
        droplet_dict = self.current_droplet_registry[id]
        self.droplet_history_registry[id] = droplet_dict

    def _get_centroids(self, droplet_dict):
        return [(droplet_dict[x].centroid) for x in droplet_dict]

    def update(self, new_droplet_dict=None, this_frame=None, BACK=False):
        """
        Update the tracker.

        TODO Tracker.update() was written as a one-way data transformation. In
        TODO hindsight, it would be useful to back up through a video file and
        TODO recalculate droplet tracking going forward. This will require tracking
        TODO updates to save a prior frame's tracking data state.

        :param new_droplet_dict: dict of raw droplets found in current frame
        :param this_frame: current frame number, used in corrections
        :return: winnowed droplet dict, filtered for already found droplets,
        """

        if len(new_droplet_dict) != 0:
            self._first_droplet = min(new_droplet_dict)
        else:
            self._first_droplet = 0

        # if this_frame == 45:
        #     debug_catcher = True

        # Placeholder. If we don't automatically identify any matched droplets in
        # this frame, but our correction file has an entry to be added in the frame,
        # there's an edge case that needs this to exist.
        matched_ids = OrderedDict()

        # 0. Candidate registry is populated with new droplets.
        if new_droplet_dict:
            self.droplet_candidate_registry = new_droplet_dict.copy()

        # 1. Bump all ages in history. (Newest goes to age 1.)
        for id in self._ageing:
            self._ageing[id] += 1

        # 2. Remove history droplets with age greater than FRAMES_BEFORE_DEREGISTER
        for id in [
            x for x in self._ageing if self._ageing[x] > self._FRAMES_BEFORE_DEREGISTER
        ]:
            self._deregister(id)

        # 3. Move current droplets to history. (Newest ones are now age 0.)
        for id in list(
            self.current_droplet_registry
        ):  # Use list, so we don't mutate index.
            self._copy_to_history(id)
            self.current_droplet_registry.pop(id)

        # 4. Current should be empty: add new droplets to current.
        if len(self.current_droplet_registry) > 0:
            sys.exit(
                "Oops. self.current_droplet_registry should be empty, "
                "but it still has {} droplets in it!"
            ).format(len(self.current_droplet_registry))
        else:
            for droplet in self.droplet_candidate_registry:
                self._register(self.droplet_candidate_registry[droplet])
            self.droplet_candidate_registry.clear()

        # 5. If we have droplets in this frame and history, compare distances.
        if (
            len(self.current_droplet_registry) > 0
            and len(self.droplet_history_registry) > 0
        ):
            # Without either current droplets or droplets in history, a droplet
            # comparison doesn't make sense!

            # Create an MxN array of distances between each known droplet and
            # each new droplet center.
            current_droplet_centroids = np.array(
                self._get_centroids(self.current_droplet_registry)
            )
            droplet_history_centroids = np.array(
                self._get_centroids(self.droplet_history_registry)
            )

            distances = distance.cdist(
                droplet_history_centroids, current_droplet_centroids, "euclidean"
            )

            # Generate sorted list of rows, smallest distance first.
            distance_row_sort = distances.min(axis=1).argsort()
            # And the same for columns.
            distance_column_sort = distances.argmin(axis=1)[distance_row_sort]

            # Let's visualize distances.

            # This is now the default. I started with the thought that we might
            # need to have a quiet mode, but went the other way, not only chattering
            # in the output, but offering to save the colorful console output to
            # an html log file.

            distance_highlight_column = distance_column_sort[0] + 1
            # (+1 because we're adding droplet numbers to the left side of
            # the table.)
            distance_highlight_row = distance_row_sort[0]

            if self._SHOW_DROPLET_TABLE and self._VERBOSE:
                printc("\nDistance", "bright red")
                print(
                    self._print_distance_array(
                        distances,
                        self.droplet_history_registry.keys(),
                        self.current_droplet_registry.keys(),
                        highlight_column=distance_highlight_column,
                        highlight_row=distance_highlight_row,
                        color="red",
                    )
                )

            # print("distance_row_sort: {}".format(distance_row_sort))  # Debug
            # print(
            #     "self.droplet_history_registry.keys(): {}".format(
            #         list(self.droplet_history_registry.keys())
            #     )
            # )  # Debug

            # 6. Create shape comparison matrix for history vs current.
            current_droplet_contours = []
            for id in self.current_droplet_registry:
                current_droplet_contours.append(
                    self.current_droplet_registry[id].contour
                )

            droplet_history_contours = []
            for id in self.droplet_history_registry:
                droplet_history_contours.append(
                    self.droplet_history_registry[id].contour
                )

            shape_similarity = np.zeros(
                (len(droplet_history_contours), len(current_droplet_contours)),
                dtype=float,
            )

            for row_index, history_contour in enumerate(droplet_history_contours):
                for col_index, current_contour in enumerate(current_droplet_contours):
                    raw_similarity_score = cv2.matchShapes(
                        history_contour, current_contour, cv2.CONTOURS_MATCH_I2, 0
                    )
                    # Biiiiig numbers. (Mostly not dealing well with 0 and inf.) I
                    # should probably do a log transform on the raw hu moments first,
                    # and do my own calcs, but matchShapes is convenient, and it'll be
                    # in the right ballpark.
                    transformed_score = abs(log_transform(raw_similarity_score))
                    if 308.0 < transformed_score < 308.5:
                        # Edge case, clsoe to 308.25 from float; too few pixels for
                        # moments to work.
                        transformed_score = 0.5  # SWAG that seems to mostly work.
                    shape_similarity[row_index, col_index] = transformed_score

            # Use an array mask to filter out large numbers and (effectively) zeroes
            # and less.
            mshape_similarity = shape_similarity
            # mshape_similarity = ma.masked_outside(shape_similarity, 0.000001, 100.0)

            # We're going to use the distance sort to drive the decision order.
            # However, here the similarity matrix will highlight the smallest similarity
            # value, which may not match the distance table.

            shape_row_sort = mshape_similarity.min(axis=1).argsort()
            shape_column_sort = mshape_similarity.argmin(axis=1)[shape_row_sort]
            shape_highlight_column = shape_column_sort[0] + 1
            shape_highlight_row = shape_row_sort[0]

            if self._SHOW_DROPLET_TABLE and self._VERBOSE:
                printc("Similarity", "bright blue")
                print(
                    self._print_distance_array(
                        mshape_similarity,
                        self.droplet_history_registry.keys(),
                        self.current_droplet_registry.keys(),
                        highlight_column=shape_highlight_column,
                        highlight_row=shape_highlight_row,
                        color="bright blue",
                    )
                )

            if self._SHOW_DROPLET_SUMMARY and self._VERBOSE:

                # Ditto on default.

                new_string = " ".join(
                    [
                        "{: >7}".format(list(self.current_droplet_registry.keys())[x])
                        for x in distance_column_sort
                    ]
                )
                old_string = " ".join(
                    [
                        "{: >7}".format(list(self.droplet_history_registry.keys())[x])
                        for x in distance_row_sort
                    ]
                )
                distance_string = " ".join(
                    [
                        "{: >7.2f}".format(distances[x, y])
                        for x, y in zip(distance_row_sort, distance_column_sort)
                    ]
                )

                # similarity_string = " ".join(
                #     [
                #         "{: >7.2f} ({},{})".format(mshape_similarity[x, y], x, y)
                #         for x, y in zip(shape_row_sort, shape_column_sort)
                #     ]
                # )  # Debug - x,y of smallest similarity number.

                similarity_string = " ".join(
                    [
                        "{: >7.2f}".format(mshape_similarity[x, y])
                        for x, y in zip(distance_row_sort, distance_column_sort)
                    ]
                )
                similarity_string = re.sub(r"--", "     --", similarity_string)
                print("       new {}".format(new_string))
                print("       old {}".format(old_string))
                print("  distance {}".format(distance_string))
                print("similarity {}\n".format(similarity_string))

            # 7. ...back to making decisions on which droplets might be
            #       previously seen...

            #    For the time being, it looks like multiplying distance by our
            #    similarity number gives us a decent indicator of whether a droplet
            #    could be a re-sighting of a prior droplet. Let's start with
            #    (d * s) < 5 as starting point for our guesses.

            # Sets used to track if a row/column pair has been used.
            used_rows = set()
            used_columns = set()
            matched_ids = OrderedDict()

            combinations_to_try = zip(distance_row_sort, distance_column_sort)
            for row, column in combinations_to_try:

                if row in used_rows or column in used_columns:
                    # Skip this combination, as this pair has been matched.
                    # printc("{}, {}".format(row, column), 'bright cyan') # Debug.
                    continue

                similarity_factor = mshape_similarity[row, column]
                confidence = distances[row, column] * similarity_factor

                # Communicate.
                if confidence > self._CONFIDENCE_THRESHOLD:
                    # Not a winner. This droplet isn't one we've seen before.
                    if self._VERBOSE:
                        printc(
                            "Confidence: - {:.2f} - Droplets {} and {} are {:.2f} pixels apart, similarity = {:.2f}".format(
                                confidence,
                                list(self.droplet_history_registry.keys())[row],
                                list(self.current_droplet_registry.keys())[column],
                                distances[row, column],
                                mshape_similarity[row, column],
                            ),
                            "red",
                        )
                elif distances[row, column] > self._DISTANCE_THRESHOLD:
                    # Not a winner. This droplet isn't one we've seen before.
                    if self._VERBOSE:
                        printc(
                            "Droplets {} and {} are {:.2f} pixels apart, greater than threshold of {}".format(
                                list(self.droplet_history_registry.keys())[row],
                                list(self.current_droplet_registry.keys())[column],
                                distances[row, column],
                                self._DISTANCE_THRESHOLD,
                            ),
                            "red",
                        )
                else:
                    if self._VERBOSE:
                        printc(
                            "Confidence: + {:.2f} - Droplets {} and {} are {:.2f} pixels apart, similarity = {:.2f}".format(
                                confidence,
                                list(self.droplet_history_registry.keys())[row],
                                list(self.current_droplet_registry.keys())[column],
                                distances[row, column],
                                mshape_similarity[row, column],
                            ),
                            "green",
                        )

                    # self.distance_research["accepted"][
                    #     (
                    #         list(self.droplet_history_registry.keys())[row],
                    #         list(self.current_droplet_registry.keys())[column],
                    #     )
                    # ] = distances[row, column]

                    # Remember the matched pair, and we'll update our registries
                    # when we're done..
                    original_droplet_id = list(self.droplet_history_registry.keys())[
                        row
                    ]
                    new_droplet_id = list(self.current_droplet_registry.keys())[column]
                    matched_ids[new_droplet_id] = original_droplet_id

                    # Add the info to our tracking sets, so we don't look at
                    # these again.
                    used_rows.add(row)
                    used_columns.add(column)

            if self._VERBOSE:
                print()

            # Loop over all matched droplet pairs, make needed registry changes
            # for corrections.

            for new_droplet_id in matched_ids:
                original_droplet_id = matched_ids[new_droplet_id]

                # Injecting droplet corrections.
                # There are three cases we're interested in.
                # Two happen inside this loop, looking at the matches we've found:
                #   1. Don't make a droplet connection at all, even though we have
                #      a match.
                #   2. Make a droplet connection other than the one that matched.

                # And the third case is new droplet assignments we didn't catch:
                #   3. Make a droplet connection when one wasn't matched at all.

                if (
                    new_droplet_id in self._droplet_corrections
                    and self._droplet_corrections[new_droplet_id] is None
                ):
                    # Case 1 - just skip this droplet
                    if self._VERBOSE:
                        printc(
                            "Droplet correction: droplet {} will *not* be connected to droplet {}".format(
                                new_droplet_id, original_droplet_id
                            ),
                            "red",
                        )

                    # self.distance_research["corrected"][
                    #     (original_droplet_id, new_droplet_id)
                    # ] = 0

                    continue

                elif (
                    new_droplet_id in self._droplet_corrections
                    and original_droplet_id != self._droplet_corrections[new_droplet_id]
                ):
                    # Case 2 - substitute new linkage
                    if self._VERBOSE:
                        printc(
                            "Droplet correction: droplet {} will be connected to droplet {} instead of {}".format(
                                new_droplet_id,
                                self._droplet_corrections[new_droplet_id],
                                original_droplet_id,
                            ),
                            "red",
                        )
                    original_droplet_id = self._droplet_corrections[new_droplet_id]

                self._process_droplet_connection(new_droplet_id, original_droplet_id)

        # And Case 3: correction droplets captured in this frame but were
        # otherwise ignored.

        for new_droplet_id in self._droplet_corrections:

            if (
                new_droplet_id in self._droplet_master.index_by_frame[this_frame]
                and new_droplet_id not in matched_ids
            ):

                if self._droplet_corrections[new_droplet_id] is None:
                    # Oops. If we're trying to connect one of the droplets in this frame
                    # to a droplet in a prior frame. If this droplet correction doesn't
                    # specify a droplet to connect to, then it's an error.

                    if self._VERBOSE:
                        printc(
                            "Droplet correction oops: droplet {} doesn't have a prior connection.".format(
                                new_droplet_id
                            ),
                            "red",
                        )
                    continue

                else:
                    if self._VERBOSE:
                        printc(
                            "Droplet correction: droplet {} will be connected to droplet {}.".format(
                                new_droplet_id,
                                self._droplet_corrections[new_droplet_id],
                            ),
                            "red",
                        )

                self._process_droplet_connection(
                    new_droplet_id, self._droplet_corrections[new_droplet_id]
                )

        return self.current_droplet_registry

    ###

    def _process_droplet_connection(self, new_droplet_id, original_droplet_id):
        """
        Utility function to add droplet connections
        :param new_droplet_id:
        :param old_droplet_id:
        """
        if self._VERBOSE:
            print(
                "New droplet {} is the same as droplet {} from frame {}.".format(
                    new_droplet_id,
                    original_droplet_id,
                    self._droplet_master.index_by_droplet[original_droplet_id].frame,
                )
            )

        # Add new location data to original droplet.
        self._droplet_master.index_by_droplet[original_droplet_id].relocate(
            self._droplet_master.index_by_droplet[new_droplet_id]
        )

        # Jigger our registries, moving the historical droplet up to current,
        # and erasing most traces of the new one.
        new_droplet_data = self.current_droplet_registry[new_droplet_id]
        new_droplet_data.id = original_droplet_id

        # Remove the original droplet from our history, including ageing...
        self._deregister(original_droplet_id)
        # ...recreate it the current registry with the old id number, which is
        # picked up from the internal droplet data...
        self._register(new_droplet_data)
        # ...and remove the found duplicate droplet from the current list.
        self._deregister_current_housekeeping(new_droplet_id)

        if self._VERBOSE:
            print()  # Last blank line before next frame.

    ###

    def _print_distance_array(
        self,
        data_array,
        prior_frame_droplet_ids,
        new_frame_droplet_ids,
        highlight_column=None,
        highlight_row=None,
        color="red",
    ):
        """
        Pretty-printer for numpy distance/shape arrays

        :param prior_frame_droplets: OrderedDict of frame droplet centroids,
                                     keyed by droplet #
        :param new_frame_droplets: Same, for the incoming frame
        :param highlight_column: Column to highlight from sort
        :param highlight_row: And row to highlight.
        :param color: Highlight color.

        :return: Unicode string ready for printing to ANSI console.

        """
        # Float formatting and alignment appear to be broken in
        # PrettyTable, and padding width shows no difference between 0 and 1. Hmpf.
        table = PrettyTable(
            border=False,
            left_padding_width=0,
            right_padding_width=0,
            padding_width=0,
            float_format=".2",
            align="r",
        )

        # Add initial blank field to header for left-side droplet numbers
        column_headers = [""] + list(
            new_frame_droplet_ids
        )  # Convert numpy array to plain list.
        # Left side numbers, from prior frame.
        row_leads = list(prior_frame_droplet_ids)  # Ditto.
        rows, columns = data_array.shape

        # row_holder is a list of row lists.
        row_holder = []
        # Column header highlight - this column contains the smallest value.
        column_headers[highlight_column] = (
            start_color(color) + str(column_headers[highlight_column]) + stop_color()
        )

        for row in range(rows):
            # Have to do our own float formatting. row_leads are the prior
            # frame droplet numbers.
            row_list = [row_leads[row]] + [
                "{: 4.2f}".format(x) for x in list(data_array[row])
            ]
            if highlight_column:
                # Highlight the column with the smallest value, hitting each row
                # as it goes by.
                row_list[highlight_column] = (
                    start_color(color) + str(row_list[highlight_column]) + stop_color()
                )
            if highlight_row:
                # List comprehension to light up all value_1_values in the highlighted row.
                if row == highlight_row:
                    row_list = [
                        start_color(color) + str(row_list[x]) + stop_color()
                        for x in range(len(row_list))
                    ]
            # And add the row to our holder.
            row_holder.append(row_list)

        # Assemble the parts.
        table.field_names = column_headers
        for row in row_holder:
            table.add_row(row)

        return "\n" + table.get_string() + "\n"
