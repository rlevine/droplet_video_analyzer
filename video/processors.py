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

from collections import OrderedDict, defaultdict
import time
import cv2
import numpy as np
from math import trunc
import os
import re

import config.common as config
from droplet.Droplet import Droplet
from frame.Frame import Frame
from frame.Labeler import Labeler
from utils.Csv import CsvFile
from utils.frame_label import add_frame_header_text
from utils.video import remove_alpha_channel
from utils.video import threshold_and_find_droplets
from utils.video import calculate_fps
from utils.video import add_alpha_channel
from utils.ffmpeg_processing import get_normalized_audio_level_by_frame
from droplet_video_analyzer.parts import get_filename_from_path
from utils.common import printc, ess
from config.common import white
from video.FrameDispenser import FrameDispenser
from grapher.Grapher import Grapher
from tracker.Tracker import Tracker


class VideoFilePreprocessor:
    def __init__(
        self, file_path=None, threshold=None, border_width=None, VERBOSE=False
    ):
        """
        Video Preprocessor
        Runs through entire video file without interruption, and creates a master catalog of
        frames and droplets.

        Doing an initial scan of the video file started as a way to get tlhe exact number
        of frames in the video file, so we could display that number on frame one of
        the output annotated video file. (Sorta like needing to paginate an entire
        document before "page x of y" can be added to the first page.) I had to read
        through the entire file to get an accurate frame count, as the opencv
        source.get(cv2.CV_CAP_PROP_FRAME_COUNT) file frame count property is only a guess
        at the frame count, if it's supported in a particular implementation.

        (The properties identifiers are integer constants.
        Names are here: https://docs.opencv.org/2.4/modules/highgui/doc/reading_and_writing_images_and_video.html#videocapture-get)

        And then, as the droplet and video data classes evolved, and since we have to
        loop through all the frames, and because it was surprisingly fast, this scan
        morphed into collecting all the other info about the droplets we find.

        VideoFilePreprocessor.droplet_counts_by_frame is a list of the total number of found
        droplets in each frame, without any work done to eliminate double-counting from
        single droplets appearing multiple times in a sequence of frames. Everything
        after this scan is either figuring out which droplets are duplicates or making
        pretty output.

        The Video object video_master is the root for all the droplet and frame instance
        data for the entire video file.

        :param file_path: str absolute path to video file
        :param threshold: int image brightness threshold for
        :param border_width:
        :param VERBOSE:
        """

        # self.file_path = file_path

        self.index_frame_number = None
        self.counting_frame_number = None

        self._second_count = 0
        self.droplet_counts_by_frame = []

        # pixel width of border to ignore
        self.border_width = border_width
        # integer from 0-255 to threshold
        self.threshold = threshold
        # absolute video file path
        self.video_file_path = file_path

        self.good_file = True

        self.VERBOSE = VERBOSE

        # Scan the video file and collect frame and droplet info.
        self.scan()

        # self._frame.key=Frame

    @property
    def frame(self, frame_number):
        return self._frame[frame_number]

    @property
    def frames(self):
        return self._frames

    def _initialize_data(self):
        # Frame and droplet data
        self._frames = OrderedDict()

        # Master indices for droplet info
        # Returns a droplet.
        self.index_by_droplet = {}
        # Returns a list of frame numbers.
        self.index_by_frame = defaultdict(list)
        # Returns a list of droplets with key (int) number of pixels.
        self.index_by_area = defaultdict(list)

        self.second_count = 0
        self.droplet_counts_by_frame = []

    def add_frame(self, id):
        """
        Add new frame instance to this Video.
        :return Frame object
        """
        f = Frame(id)
        self._frames[f.id] = f
        return f

    def scan(self):

        """
        This started as a quick, initial scan of the supplied video file to get a frame
        count for labeling and a droplet count for scaling graphs. It evolved into getting
        all the droplet info for the file; grabbing all the extra info wasn't much slower,
        and there are advantages to having all the droplet data assembled before starting
        any analysis.

        The architectural intent is to generate and store meta-data, but not store video
        frame data.
        """

        scan_start_time = time.time()  # For shits and giggles.

        # source = cv2.VideoCapture(self.video_file_path)

        self._initialize_data()

        if self.VERBOSE:
            print("\nInitial scan of {}\n".format(self.video_file_path))

        # if source.isOpened() is False:
        #     self.good_file = False
        #     return

        dispenser = FrameDispenser(self.video_file_path)

        # Reset master numbering for droplets, in case this isn't our first rodeo.
        Droplet.master_count = 1

        while True:

            # Spin through all the frames.
            frame = dispenser.next()
            self.index_frame_number = dispenser.index_frame_number
            self.counting_frame_number = dispenser.counting_frame_number

            if dispenser.is_empty:
                break

            frm = self.add_frame(self.index_frame_number)

            self._progress_indicator()

            # Get some droplets.
            droplets, thresholded_frame = threshold_and_find_droplets(
                frame, self.threshold, self.border_width
            )
            self.droplet_counts_by_frame.append(len(droplets))

            # Let's fill in the droplet data structure.

            # Setup for floodFill to get pixel area
            h, w = frame.shape[:2]
            mask = np.zeros((h + 2, w + 2), np.uint8)
            flood_connectivity = 8
            floodfill_flags = flood_connectivity | cv2.FLOODFILL_MASK_ONLY

            for droplet in droplets:

                drp = frm.add_droplet()

                # Centroid is set when we add the contour, and frame number we know.
                drp.contour = droplet
                drp.frame = self.index_frame_number

                # Pixel area takes a little more work.
                # (This is done here, rather than in Droplet, because we need
                # access to the frame data to calculate the droplet area.)

                # The moment-derived area, m00, isn't pixel-accurate in opencv,
                # nor is cv2.contourArea(), which probably just uses the m00 code.

                # Doing a fill of the contour with cv2.floodFill returns the actual
                # contour area in pixels. (This seems to be an undocumented return. :)

                # I'm using the first point of the contour, contour[0][0],
                # for the seed point coordinate for floodFill.

                mask[:] = 0
                seed_point = tuple(droplet[0][0])
                drp.area = cv2.floodFill(
                    thresholded_frame,
                    mask,
                    seed_point,
                    white,
                    (20,) * 3,
                    (20,) * 3,
                    floodfill_flags,
                )[0]

                self.index(drp, frm)  # Adds droplet to convenience indices.

        # else:
        #     break

        scan_end_time = time.time()
        fps = calculate_fps(scan_start_time, scan_end_time, self.counting_frame_number)

        if self.VERBOSE:
            print(
                "\n\nCounted {} frames and {} droplets,\nprocessed at {:2.0f} frames per second.\n".format(
                    self.counting_frame_number, sum(self.droplet_counts_by_frame), fps
                )
            )

    def _progress_indicator(self):

        # Pretty progress indicator
        if self.index_frame_number % 30 == 0:
            self._second_count += 1
            if self.VERBOSE:
                print(".", end="")
            if self._second_count % 30 == 0:
                if self.VERBOSE:
                    print()

    def index(self, droplet, frame):
        """
        Create index entries for droplet.
        """
        self.index_by_frame[frame.id].append(droplet.id)
        self.index_by_droplet[droplet.id] = droplet
        self.index_by_area[trunc(droplet.area)].append(droplet.id)


class VideoFrameProcessor:
    def __init__(
        self,
        file_path=None,
        image_capture_file_output_path=None,
        video_file_output_path=None,
        output_frames=1,
        image_threshold=None,
        similarity_threshold=None,
        distance_threshold=None,
        history_frames_to_consider=None,
        border_width=None,
        video_master=None,
        corrections=None,
        hide_droplet_history_in_video=None,
        csv_file=None,
        CAPTURE_VIDEO=False,
        VERBOSE=False,
        DEBUG=False,
    ):

        self._frames = OrderedDict()
        self._corrections = corrections

        self.file_path = file_path
        self._image_capture_file_output_path = image_capture_file_output_path
        self._video_file_output_path = video_file_output_path
        self._frame_dispenser = FrameDispenser(self.file_path, PROCESSED_HISTORY=True)
        self.frame_shape = self._frame_dispenser.shape
        # Current unprocessed video frame
        self._frame = None
        # Current finished frame
        self.processed_frame = None

        self.index_frame_number = None
        self.counting_frame_number = None

        self.frame_droplet_count = 0
        self.video_total_droplet_count = 0
        self.video_total_unprocessed_droplet_count = 0
        self.frame_pixel_area = 0
        self.video_total_pixel_area = 0

        # pixel width of border to ignore
        self.border_width = border_width
        # integer from 0-255 to threshold
        self.image_threshold = image_threshold
        # increment for interactve threshold adjustment
        self._image_threshold_increment = 2
        # flag to force data rescan of video file
        self._file_rescan_needed = False
        # flag to indicate we're processing a frame again
        self._reprocessing = False
        # droplet similarity threshold
        self.similarity_threshold = similarity_threshold
        # Number of past frames to consider for similarity
        self.history = history_frames_to_consider
        # Max distance limit between related droplets
        self.distance_threshold = distance_threshold

        self._video_master = video_master
        self.file_length_in_frames = len(video_master.frames)

        self._HIDE_DROPLET_HISTORY = hide_droplet_history_in_video

        self._csv_file = csv_file
        # self._CAPTURE_VIDEO = CAPTURE_VIDEO
        # self._output_frames = output_frames
        self._VERBOSE = VERBOSE
        self._DEBUG = DEBUG

        # Set up our on-screen droplet graph.
        self._tiny_graph = Grapher(
            (50, 915),
            x_label='seconds',
            lower_x_label='audio',
            y_label='droplets/frame',
            y2_label='cumulative droplets',
            max_y_data=max(self._video_master.droplet_counts_by_frame),
            max_y2_data=sum(self._video_master.droplet_counts_by_frame),
            y_axis_height=150,  # Hard-coded.
        )

        # Initialize droplet tracker
        self._droplet_tracker = Tracker(
            frames_before_deregister=self.history,
            confidence_threshold=self.similarity_threshold,
            distance_threshold=self.distance_threshold,
            droplet_corrections=self._corrections,
            droplet_master=self._video_master,
            VERBOSE=VERBOSE,
        )

        (video_frame_width, video_frame_height) = self.frame_shape

        #
        # Experiment in getting audio data for display.
        #

        self.audio_data_by_frame = get_normalized_audio_level_by_frame(self.file_path)

        # if self._CAPTURE_VIDEO:
        #     # Open the output file.
        #     self.video_output = cv2.VideoWriter(
        #         self._video_file_output_path,
        #         cv2.VideoWriter_fourcc("M", "P", "V", "4"),
        #         30,
        #         (1920, 1080),
        #         # (int(video_frame_width), int(video_frame_height)),
        #         # (int(video_frame_height), int(video_frame_width)),
        #     )

        # if cv2.VideoWriter.isOpened(self.video_output):
        #     pass

    def has_no_more_frames(self):
        if self.index_frame_number == self.file_length_in_frames:
            return True

    def next_frame(self):
        self._rescan_check()
        if self._reprocessing:
            # If we're coming back from reprocessing a frame, we want 'next'
            # to redisplay the prior, just-reprocessed frame, not advance.
            # Don't grab a new frame, and don't advance the numbers.
            pass
        else:
            self._frame = self._frame_dispenser.next()
            if self._frame_dispenser.is_empty:
                # The dispenser doesn't know it's empty until it tries to
                # dispense a frame and doesn't find one.
                return
            self.index_frame_number = self._frame_dispenser.index_frame_number
            self.counting_frame_number = self._frame_dispenser.counting_frame_number
        if self._frame_dispenser.in_history:
            return self._frame
        else:
            return self._process(self._frame, self.index_frame_number)

    def previous_frame(self):
        self._rescan_check()
        if self._reprocessing:
            pass
        else:
            # Dispenser.previous will return a saved, processed frame.
            self._frame = self._frame_dispenser.previous()
            self.index_frame_number = self._frame_dispenser.index_frame_number
            self.counting_frame_number = self._frame_dispenser.counting_frame_number

        return self._frame

    def reprocess_last_frame(self):
        return self._process(self._frame, self.index_frame_number)

    def redisplay_last_processed_frame(self):
        return self.processed_frame

    def capture_current_frame(self):
        image_capture_file_name_next_count = 1
        while os.path.exists(self._image_capture_file_output_path):
            self._image_capture_file_output_path = re.sub(
                r"_\d+\.png",
                rf"_{str(image_capture_file_name_next_count)}.png",
                self._image_capture_file_output_path,
            )
            image_capture_file_name_next_count += 1
        cv2.imwrite(self._image_capture_file_output_path, self.processed_frame)
        return self.processed_frame

    def image_threshold_up(self):
        self.image_threshold += self._image_threshold_increment
        self._file_rescan_needed = True

    def image_threshold_down(self):
        self.image_threshold -= self._image_threshold_increment
        self._file_rescan_needed = True

    def _rescan_check(self):
        if self._file_rescan_needed:
            self._video_master.threshold = self.image_threshold
            self._video_master.scan()
            self._file_rescan_needed = False
            self._reprocessing = True

    def _process(self, frame, index_frame_number):

        """"""

        droplet_data = self._video_master.frames[index_frame_number].droplets
        # print(
        #     "frame: {}, {} droplets found".format(index_frame_number, len(droplet_data))
        # )  # Debug

        self.video_total_unprocessed_droplet_count += len(droplet_data)

        # We want the grayscale frame with the border cleaned up, but
        # we don't want the droplets.
        thresholded_frame = threshold_and_find_droplets(
            frame, self.image_threshold, self.border_width, DROPLET_SCAN=False
        )

        # Introduce this frame.
        if self._VERBOSE:
            areas = [droplet_data[x].area for x in droplet_data]
            if len(areas) > 0:
                areas_string = "(" + " ".join([str(x) for x in areas]) + ")"
            else:
                areas_string = ""

            printc(
                "----- Frame {}: {} raw droplet{}, {} pixel{} {} ---------------".format(
                    self.index_frame_number + 1,
                    len(droplet_data),
                    ess(len(droplet_data)),
                    sum(areas),
                    ess(sum(areas)),
                    areas_string,
                ),
                "purple",
            )

        #
        # Tracker interlude
        #

        # Most of the shenanigans happen here. All the droplets go out, but
        # some don't come back.
        winnowed_droplets = self._droplet_tracker.update(
            new_droplet_dict=droplet_data, this_frame=self.index_frame_number
        )

        #
        # Beginning of pretty video frame.
        #

        # Convert frame back to color so we can write in color on it.
        self.processed_frame = cv2.cvtColor(thresholded_frame, cv2.COLOR_GRAY2RGB)

        self.frame_droplet_count = 0
        self.frame_pixel_area = 0
        frame_area_correction = 0

        #
        # Highlight and label found droplets.
        #

        labels = Labeler(
            index_frame_number,
            frame_shape=self.frame_shape,
            VERBOSE=self._VERBOSE,
            DEBUG=self._DEBUG,
        )

        for droplet_id in winnowed_droplets:

            new_droplet = False  # Our flag for dealing with counts and areas later.

            # Check to see if this droplet was matched to a prior frame.
            if (
                droplet_id
                not in self._video_master.index_by_frame[self.index_frame_number]
            ):
                # We think the droplet is a match to a prior frame. :)
                new_droplet = True

                # "New droplet" as in "this droplet number isn't one we
                # expected in this frame."

                # The default droplet pixel area is the area of the most recent
                # droplet sighting. We might be able to do better here, for
                # instance getting the max area from the multiple sightings,
                # but for now let's be simple, and use the original area.
                # We might need to subtract out the current contour area
                # later: save the correction.
                frame_area_correction += self._video_master.index_by_droplet[
                    droplet_id
                ].area

            # Get the data for this droplet.
            droplet = self._video_master.index_by_droplet[droplet_id]

            label = labels.add_label(droplet)

            if not new_droplet:
                self.frame_droplet_count += 1
                if not self._reprocessing:
                    self.video_total_droplet_count += 1

            # If we need video, either for captured file or end-user display
            # while processing or to capture the top 10 frame images.
            # if not HIDE_VIDEO or CAPTURE_VIDEO or TOP_10:

            if not self._HIDE_DROPLET_HISTORY:
                # Draw outlines of any prior generations.
                if droplet.generations() >= 2:
                    # Contour history to draw before the green box.
                    for contour in droplet.contour_history():
                        self.processed_frame = cv2.drawContours(
                            self.processed_frame, contour, -1, config.amber
                        )

            # Draw red bounding box around this frame's contour.
            label.draw_contour_bounding_box(
                self.processed_frame, color=config.bright_red, thickness=1
            )

            # Mark the center with a single red pixel.
            # (This will never be seen, unless the frame is grabbed and
            # magnified. :)
            integer_droplet_center = tuple([int(n) for n in droplet.centroid])
            cv2.line(
                self.processed_frame,
                integer_droplet_center,
                integer_droplet_center,
                config.bright_red,
                1,
            )

            # Getting the droplet area has already been done for us in the file scan.
            area = droplet.area

            # if new_droplet:
            self.frame_pixel_area += area
            self.video_total_pixel_area += area

            if self._csv_file:
                self._csv_file.update_csv_row(
                    str(self.counting_frame_number),
                    str(droplet.initial_id),
                    [droplet_id, area],
                )

        # if self.index_frame_number >= 116:  # Debug breakpoint catcher
        #     debug_catcher = True

        # Draw all the labels.
        labels.draw(self.processed_frame)

        # Add some frame labeling.
        self.processed_frame = add_frame_header_text(
            self.processed_frame,
            get_filename_from_path(self.file_path),
            self.counting_frame_number,
            self.file_length_in_frames,
            self.frame_droplet_count,
            self.frame_pixel_area,
            self.video_total_droplet_count,
            self.video_total_unprocessed_droplet_count,
            self.video_total_pixel_area,
            self.image_threshold,
            self.history,
            self.similarity_threshold,
            self.distance_threshold,
        )

        # Update and draw the droplet graph.
        if self._reprocessing:
            self._tiny_graph.reset_max_y(
                max(self._video_master.droplet_counts_by_frame)
            )

        else:
            self._tiny_graph.update(
                len(droplet_data), self.audio_data_by_frame[self.index_frame_number]
            )
        self._tiny_graph.canvas = self.processed_frame
        self.processed_frame = self._tiny_graph.draw_graph()

        # Composite annotations on to original video frame.
        self.processed_frame = cv2.add(
            add_alpha_channel(frame),
            add_alpha_channel(self.processed_frame, transparent_color=(0, 0, 0)),
        )
        # Capture the output frame.
        # if self._CAPTURE_VIDEO:
        #     # Not sure if this is needed...
        #     self.processed_frame = remove_alpha_channel(self.processed_frame)
        #     for _ in range(self._output_frames):
        #         self.video_output.write(self.processed_frame.astype("uint8"))

        # cv2.imwrite(
        #     '/Users/CS255/Desktop/git/python/fmva/test_output_3/test.jpg',
        #     self.processed_frame,
        # )

        # Put the finished frame back into the dispenser.
        self._frame_dispenser.processed_frame_return(self.processed_frame)

        if self._reprocessing:
            self._reprocessing = False

        return self.processed_frame
