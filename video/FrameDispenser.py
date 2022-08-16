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

import cv2
import sys
from collections import deque
from collections import OrderedDict
from hashlib import md5
from utils.common import printc


class FrameDispenser:
    def __init__(
        self, file_path=None, history_size=20, PROCESSED_HISTORY=False, VERBOSE=False
    ):
        """
        Initialize video file.

        :return: string absolute file name
        """
        # Frame number used as list index. (0-based)
        self.index_frame_number = -1
        # Frame number used when people are counting. (1-based)
        self.counting_frame_number = 0
        # Number of frames in history buffer.
        self.history_retrieval_point = -1

        self.current_frame = None
        self.video_file_path = file_path

        # Frame dimensions: returns (width, height) tuple
        self.shape = None

        # Flag to get processed frames, if any, rather than raw.
        self._PROCESSED_HISTORY = PROCESSED_HISTORY
        # Externally visible flag to indicate we're returning a frame
        # from our history.
        self.in_history = False

        self._VERBOSE = VERBOSE

        # cv2 video handle
        self._video_file = None

        # Experiment: dict of hashes of all frames
        self.hash_dict = OrderedDict()

        # Buffer for raw frame history
        self._raw_buffer = None
        # Buffer for processed frames returned from upstream.
        self._processed_buffer = None
        self._buffer_size = history_size

        self.is_empty = None

        self._open_video_file()

        if self._video_file.isOpened() is False:
            sys.exit(
                "FrameDispenser cannot open video file {}!".format(self.video_file_path)
            )

    def _open_video_file(self):

        self._video_file = cv2.VideoCapture(self.video_file_path)

        # if self._VERBOSE:
        #     print("\nInitial scan of {}\n".format(self.video_file_path))

        if self._video_file.isOpened() is False:
            self.is_empty = True
            return

        self.frame_rate = round(self._video_file.get(cv2.CAP_PROP_FPS))

        self.shape = tuple(
            int(x)
            for x in [
                self._video_file.get(cv2.CAP_PROP_FRAME_WIDTH),
                self._video_file.get(cv2.CAP_PROP_FRAME_HEIGHT),
            ]
        )

        self._raw_buffer = deque(
            [None for x in range(self._buffer_size)], self._buffer_size
        )
        self._processed_buffer = deque(
            [None for x in range(self._buffer_size)], self._buffer_size
        )

    def _print_status(self, calling_function):
        # Debug.
        printc(
            """
            function = {}
            history_retrieval_point = {}
            _PROCESSED_HISTORY = {}
            in_history = {}
            """.format(
                calling_function,
                self.history_retrieval_point,
                self._PROCESSED_HISTORY,
                self.in_history,
            ),
            'yellow',
        )

    def next(self):

        # As currently implemented, a dispenser doesn't know it's empty until it asks
        # for a frame after the last one, as it doesn't know . I could implement a
        # look-ahead, pulling an  extra frame, but that would require figuring out an
        # elegant solution to deal with the extra frame when reversing. More work
        # than I want today. :)

        # We're in our history.
        if self.history_retrieval_point < -1:
            self.history_retrieval_point += 1
            self._increment_frame_number()
            return self._processed_buffer[self.history_retrieval_point]
        else:
            self.in_history = False

        if self.is_empty:
            # This is true when it discovers it's empty, ie when it asks for
            # another frame, and the cupboard is bare. (Think paper towel dispenser.
            # Many of us will take the last towel, frustrating the person after us.)
            return None

        got_frame, frame = self._video_file.read()

        # End of video file.
        if not got_frame:
            self.is_empty = True
            self._video_file.release()
            return None

        # Otherwise, give them the next frame.

        # Add frame to right side of buffer.
        self._raw_buffer.append(frame)
        self._increment_frame_number()
        self.current_frame = frame

        # Experiment, fingerprinting to id frames for testing.
        self._make_hash_dict_entry(self.current_frame)

        return self.current_frame

    def previous(self):

        # We've backed up through the entire buffer
        if (
            abs(self.history_retrieval_point) == self._buffer_size
            or self.index_frame_number == 0
        ):
            # Return the current frame again.
            return self.current_frame

        # Buffer remaining, back up in buffer and return frame..
        self.history_retrieval_point -= 1
        self._decrement_frame_number()
        if self._PROCESSED_HISTORY:
            self.current_frame = self._processed_buffer[self.history_retrieval_point]
        else:
            self.current_frame = self._raw_buffer[self.history_retrieval_point]

        self.in_history = True

        return self.current_frame

    def _increment_frame_number(self):
        self.index_frame_number += 1
        self.counting_frame_number += 1

    def _decrement_frame_number(self):
        self.index_frame_number -= 1
        self.counting_frame_number -= 1

    def processed_frame_return(self, frame):
        # Used by upstream processor to add a processed
        # frame to be returned instead of a raw frame when
        # traversing history.
        self._processed_buffer.append(frame)

    def _make_hash_dict_entry(
        self, frame, sample_width=100, sample_height=100, center=True
    ):
        """
        Experiment: create an md5 hash of a sample area of each frame for a fingerprint
        to identify frames in testing. (Hashing an entire 2K frame is too slow.) This
        hashes a sample from the either the upper left corner or the center of the
        frame, default is center and 100x100.

        :param frame: np video frame array
        :param sample_width: int sample size x
        :param sample_height: int sample size y
        :param center: bool
        """

        frame_height, frame_width, _ = frame.shape

        if center:
            start_x = frame_width // 2 - sample_width // 2
            start_y = frame_height // 2 - sample_height // 2
        else:
            start_x = 0
            start_y = 0

        sample = frame[
            start_y : start_y + sample_height, start_x : start_x + sample_width
        ]

        # hash: frame#
        self.hash_dict[md5(sample.tostring()).hexdigest()] = self.index_frame_number
        # frame#: hash
        # self.hash_dict[self.index_frame_number] = md5(sample.tostring()).hexdigest()
