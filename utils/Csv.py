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

from collections import OrderedDict
import csv


class CsvFile:
    def __init__(self, video_master, file_path, VERBOSE=False):
        """
        Initialize csv file.

        :return: string absolute file name
        """
        self.csv_file_path = file_path
        self._csv_data_dict = OrderedDict()

        self._load_initial_csv_data(video_master)

        self._VERBOSE = VERBOSE

    @property
    def row_count(self):
        return len(self._csv_data_dict)

    def _load_initial_csv_data(self, video_master):

        # Collect initial .csv file data dict, based on first, unwinnowed
        # pass through video file, keyed by tuple (<frame #>, <initial droplet id>)
        # Blanks in data will be filled in later with assigned droplet id and
        # updated area.

        # TODO Using named tuples might make these methods more readable.

        for frame_id, _ in enumerate(video_master.frames):
            for droplet_id in video_master.frames[frame_id].droplets:
                initial_id = (
                    video_master.frames[frame_id].droplets[droplet_id].initial_id
                )
                self._csv_data_dict[(str(frame_id + 1), str(initial_id))] = [
                    '',
                    video_master.frames[frame_id].droplets[droplet_id].area,
                    '',
                ]

    def update_csv_row(self, frame, initial_droplet_id, value):
        """
        Update with assigned droplet id and area.

        :param frame: int counting frame number
        :param droplet: int initial droplet id
        :param value: list containing assigned droplet_id, pixel area, centroid coords

        """
        (
            assigned_droplet_id,
            droplet_area,
            droplet_centroid_x,
            droplet_centroid_y,
        ) = value

        current_row = self._csv_data_dict[(str(frame), str(initial_droplet_id))]

        if str(assigned_droplet_id) == str(initial_droplet_id):
            # Isn't a duplicate of a prior droplet, ie no change in id.
            self._csv_data_dict[(str(frame), str(initial_droplet_id))] = [
                assigned_droplet_id,
                current_row[1],
                '',
            ]
        else:
            # Duplicate droplet, with new assigned id and new pixel area.
            self._csv_data_dict[(str(frame), str(initial_droplet_id))] = [
                assigned_droplet_id,
                '',
                droplet_area,
            ]
        # Add centroid coordinates to all rows.
        self._csv_data_dict[(str(frame), str(initial_droplet_id))].extend(
            [
                droplet_centroid_x,
                droplet_centroid_y,
            ]
        )

    def write(self):

        """
        Write the .csv data file.
        """

        csv_file = open(self.csv_file_path, "w", newline="")
        csv_writer = csv.writer(csv_file, dialect="excel")
        # Header row.
        csv_writer.writerow(
            [
                'assigned_droplet_id',
                'initial_droplet_id',
                'frame',
                'initial_pixels',
                'duplicate_pixels',
                'centroid_x',
                'centroid_y',
            ]
        )

        # Rearrange, sort and write csv data.

        # We had to use a unique key for our dict, but now we can untangle the data,
        # putting the assigned (and potentially duplicated) droplet id first.
        data_list = []
        for key in self._csv_data_dict:
            (frame_count, droplet_id) = key
            data_list.append(
                [
                    self._csv_data_dict[key][0],
                    droplet_id,
                    frame_count,
                    self._csv_data_dict[key][1],
                    self._csv_data_dict[key][2],
                    self._csv_data_dict[key][3],
                    self._csv_data_dict[key][4],
                ]
            )
        # Sort the rows by the assigned droplet id.
        data_list.sort(key=lambda x: x[0])
        # Rock & roll.
        for row in data_list:
            csv_writer.writerow(row)
        csv_file.close()

        if self._VERBOSE:
            print("\nCreated data file {}.".format(self.csv_file_path))
