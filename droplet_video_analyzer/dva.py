#!/usr/bin/env python

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
import time
import sys

from utils.cl_args import get_test_args
from utils.cl_args import get_options
from droplet_video_analyzer.parts import (
    manage_display_and_keyboard,
    set_up_output_filenames,
    get_filename_from_path,
    unpack_input_files,
    resolve_directory,
)
from droplet_video_analyzer.Dispatcher import Dispatcher
from utils.corrections import get_correction_file_data
from utils.Logger import Transcript
from utils.video import calculate_fps
from utils.Csv import CsvFile
from utils.ffmpeg_processing import add_audio
from video.processors import VideoFrameProcessor
from video.processors import VideoFilePreprocessor

import warnings


# Remove annoyance.
warnings.filterwarnings(
    'ignore',
    r'Format strings passed to MaskedConstant are ignored',
)


def main():

    # If running from an IDE, set TEST to True to use test command line arguments
    # defined in utils.cl_args.get_test_args()
    # Or, from the command line, using the ---test flag will read the same values,
    # ignoring the rest of the command line flags.

    TEST = False
    TEST = True  # Comment this in to use test args in utils/cl_args.py.

    TEST_ARGS = get_test_args(TEST)

    # Retrieve argparse namespace and convert to dict.
    argv = vars(get_options(TEST_ARGS=TEST_ARGS))

    # Housekeeping and config set-up

    DEBUG = argv["DEBUG"]
    VERBOSE = argv["VERBOSE"]
    INTERACTIVE = argv["INTERACTIVE"]
    CAPTURE_VIDEO = argv["CAPTURE_VIDEO"]
    HIDE_VIDEO = argv["HIDE_VIDEO"]
    INCLUDE_AUDIO = argv["INCLUDE_AUDIO"]
    TOP_10 = argv["TOP_10"]
    CORRECTIONS = argv["CORRECTIONS"]
    HIDE_DROPLET_HISTORY = argv["HIDE_DROPLET_HISTORY"]
    LOG = argv["LOG"]
    CSV = argv["CSV"]
    video_threshold = argv["threshold"]

    # Print the command line string, if we're testing.
    if VERBOSE and TEST_ARGS:
        print("\n{}{}\n".format(get_filename_from_path(__file__), TEST_ARGS))

    input_directory = resolve_directory(dir=argv['input_directory'])
    output_directory = resolve_directory(dir=argv['output_directory'])

    video_files = unpack_input_files(
        argv['video_files'],
        input_directory=input_directory,
        output_directory=output_directory,
    )

    #
    # Main loop.
    # Process each video file.
    #

    for video_filename in video_files:

        #
        # File set-up.
        #

        video_file_input_path = video_filename

        # Set up all the output file names we'll need.
        output_files = set_up_output_filenames(
            video_file_input_path,
            argv_output_dir=video_files[video_filename]['output_dir'],
        )

        # Start saving a log file if requested.
        if LOG:
            transcript = Transcript(output_files["log_file_output_path"])

        # Check to see if a manual correction file for the source video data
        # file exists, load any data, and create a new file if there isn't one.
        if CORRECTIONS:
            droplet_corrections, correction_count = get_correction_file_data(
                correction_file_path=output_files["correction_file_path"],
                output_file_path=output_files["video_file_output_path"],
                video_threshold=video_threshold,
                frame_history=argv["frame_history"],
                droplet_similarity=argv["droplet_similarity"],
                distance_threshold=argv["distance_threshold"],
            )
        else:
            droplet_corrections = None
            correction_count = None

        # Do a scan of the video file for droplets, and create the
        # master droplet catalog for the file.

        video_master = VideoFilePreprocessor(
            video_file_input_path,
            video_threshold,
            argv["border"],
            VERBOSE=VERBOSE,
        )

        #
        # Start CSV data file, if requested.
        #
        if CSV:
            # Collect initial .csv file data
            csv_file = CsvFile(
                video_master, output_files["csv_file_output_path"], VERBOSE
            )
        else:
            csv_file = None

        #
        # Start of top 10 frames-by-droplet-counts
        #

        # Gather frame numbers for top 10 frames by number of droplets detected.
        # We'll use this to save those frames to image files, which will be useful for
        # evaluating droplet thresholding without creating an entire video file.
        # We'll also grab the droplet count for the frame with the highest count to
        # scale our frame graph.

        frame_droplet_counts = sorted(
            [
                (frame_id, video_master.frames[frame_id].droplet_count)
                for frame_id in video_master.frames
            ]
        )

        top_10_frames = [
            x[0]
            for x in sorted(frame_droplet_counts, key=lambda x: x[1], reverse=True)[:11]
        ]

        #
        # Second video pass.
        #

        # Start up a frame processor on the video file..

        frame_processor = VideoFrameProcessor(
            file_path=video_file_input_path,
            image_capture_file_output_path=output_files[
                'image_capture_file_output_path'
            ],
            video_file_output_path=output_files['video_file_output_path'],
            output_frames=argv['output_frames'],
            image_threshold=video_threshold,
            similarity_threshold=argv["droplet_similarity"],
            distance_threshold=argv["distance_threshold"],
            history_frames_to_consider=argv["frame_history"],
            border_width=argv["border"],
            video_master=video_master,
            corrections=droplet_corrections,
            hide_droplet_history_in_video=HIDE_DROPLET_HISTORY,
            csv_file=csv_file,
            CAPTURE_VIDEO=CAPTURE_VIDEO,
            VERBOSE=VERBOSE,
            DEBUG=DEBUG,
        )

        #
        # Set up an mpeg file to which to write analyzed frames.
        #

        # There's some implementation-dependent weirdness here, particularly specifying
        # the FourCC codec id. I'm running OSX 10.14.6 Mojave on a MacBook Pro. YMMV.
        # Oh, and this seems to fail on my system if it tries to open a file that
        # already exists. I've added a time-stamp in the file name to
        # reduce that likelihood.

        (video_frame_width, video_frame_height) = frame_processor.frame_shape
        #
        if CAPTURE_VIDEO:
            # Open the output file.
            video_output = cv2.VideoWriter(
                output_files["video_file_output_path"],
                # Picking an output video codec in opencv is buggy.
                # Trying to find a FourCC it likes didn't work. The settings
                # that work are all bogus entries, and it falls back to
                # H.264 in a MP4 v2 container..
                cv2.VideoWriter_fourcc("m", "p", "v", "4"),  # works, not found message
                # cv2.VideoWriter_fourcc("m", "p", "g", "4"),  # works, not supported, not found msgs
                # cv2.VideoWriter_fourcc("A", "V", "C", "1"),  # writes unreadable file
                # cv2.VideoWriter_fourcc("J", "P", "E", "G"),  # writes unreadable file
                # cv2.VideoWriter_fourcc("A", "C", "V", "1"),  # works w/msg
                # cv2.VideoWriter_fourcc("0", "0", "0", "0"),  # bogus entry, works w/msg
                30,
                (int(video_frame_width), int(video_frame_height)),
                1,
            )

        # Video frames are numbered from 00:00; 00:29 is the 30th frame in a second.
        # I'm using 0 for timecode start, and adding 1 for "frame M of N" visual, so
        # it doesn't start with 0 for a viewer of the video. I've settled on
        # "index_frame_number" and "counting_frame_number" in the code to distinguish
        # the two numbering contexts for frames.

        # index_frame_count = -1  # Vestigal, I think. Delete?

        analysis_start_time = time.time()  # Curiosity.

        #
        # Event dispatcher for actions coming back from keyboard.
        #

        dispatcher = Dispatcher(
            interactive=INTERACTIVE,
            capture_video=CAPTURE_VIDEO,
            hide_video=HIDE_VIDEO,
            top_10=TOP_10,
            csv=CSV,
        )

        # First action and frame advance count for the video frame loop.
        action = "next"
        params = {'frames_to_advance': 1}

        if CAPTURE_VIDEO or CSV or TOP_10 and not HIDE_VIDEO:
            params['back_disabled'] = True
        else:
            params['back_disabled'] = False

        #
        # Video frame loop.
        #

        while True:

            # When the end of a video file is reached,
            # the processor knows about it.
            if frame_processor.has_no_more_frames():
                break

            next_action_function = dispatcher.dispatch(action)
            display_frame = next_action_function(frame_processor)

            # If the dispatcher function returns None instead of
            # a video frame.                                              d
            if display_frame is None:

                # # Experiment in fingerprinting frame
                # print("hash_dict = {")
                # for a, b in sorted(
                #     frame_processor._frame_dispenser.hash_dict.items(),
                #     key=lambda x: x[1],
                # ):
                #     print("    '{}': {},".format(a, b))
                # print("}")

                break

            if CAPTURE_VIDEO:
                for _ in range(argv['output_frames']):
                    video_output.write(display_frame.astype("uint8"))

            # cv2.imwrite("./saved_video_frame.png", frame_processor.processed_frame)

            if not HIDE_VIDEO:
                action, params = manage_display_and_keyboard(
                    display_frame,
                    INTERACTIVE,
                    frame_processor.file_length_in_frames,
                    frame_processor.counting_frame_number,
                    params,
                )

        # We're mostly done.

        # Brags.

        analysis_end_time = time.time()

        if (not INTERACTIVE or CAPTURE_VIDEO) and VERBOSE:
            # Because interruptions.
            fps = calculate_fps(
                analysis_start_time,
                analysis_end_time,
                frame_processor.counting_frame_number,
            )
            print(
                """
    \n\n2nd pass: {} frames,\nprocessed at {:2.1f} frames per second.""".format(
                    frame_processor.counting_frame_number, fps
                )
            )
            print(
                """
{} droplets found in initial scan of video file
{} unique droplets after duplicate discovery
            """.format(
                    sum(video_master.droplet_counts_by_frame),
                    frame_processor.video_total_droplet_count,
                )
            )

        if (correction_count is not None and correction_count > 0) and VERBOSE:
            print(
                """
{} corrections made by hand (error rate {:.2f}%, {:.2f}% correct)
            """.format(
                    correction_count,
                    (correction_count / frame_processor.video_total_droplet_count)
                    * 100,
                    100
                    - (
                        (correction_count / frame_processor.video_total_droplet_count)
                        * 100
                    ),
                )
            )

        # Clean-up.

        if LOG:
            transcript.close()

        if CSV:
            # .csv data file requested?
            csv_file.write()

        if CAPTURE_VIDEO:
            video_output.release()

            # This is last, mostly because it's convenient to hang the
            # audio conversion under the CAPTURE_VIDEO test, and because it's a
            # blind launch of ffmpeg with no progress indicator. But we can time it.

            if INCLUDE_AUDIO and argv['output_frames'] == 1:
                add_audio(
                    in_file=video_file_input_path,
                    out_file=output_files["video_file_output_path"],
                    combined_file=output_files["video_audio_file_output_path"],
                    VERBOSE=VERBOSE,
                )

    # # Printing droplet distance data:for use in determining distance threshold.
    # for (orig_droplet, new_droplet) in list(
    #     droplet_tracker.distance_research["accepted"].keys()
    # ):
    #     print(
    #         "{}\t{}\t{:.2f}".format(
    #             orig_droplet,
    #             new_droplet,
    #             droplet_tracker.distance_research["accepted"][(orig_droplet, new_droplet)],
    #         ),
    #         end="",
    #     )
    #
    #     if (orig_droplet, new_droplet) in droplet_tracker.distance_research["corrected"]:
    #         print("\tcorrected")
    #     else:
    #         print()


###

if __name__ == "__main__":
    sys.exit(main())  # pragma: no cover
