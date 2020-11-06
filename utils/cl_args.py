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

import argparse


def get_test_args(TEST=False):

    if TEST:
        TEST_ARGS = ''.join(
            [
                # fmt: off

                # ' --file ', '*.mp4',
                # ' --file ', 'Surgical_01.mp4',
                # ' --file ', 'N95_05.mp4',
                # ' --file ', 'Bandana_05.mp4',
                # ' --file ', 'None_04_floater_tighter.mp4',
                # ' --file ', 'None_04_floater.mp4',
                # ' --file ', 'None_04_trimmed.mp4',
                # ' --file ', 'None_04_trimmed_more.mp4',
                # ' --file ', 'Bandana_05_20_frames.mp4',
                ' --file ', 'Fleece_04_trimmed2.mp4',
                ' --threshold ', '62',
                # ' --frame-history ', '1',
                # ' --droplet-similarity ', '30',
                # ' --distance-threshold ', '40',
                # ' --border ', '20',
                # ' --top-10',
                # ' --quiet',
                # ' --debug',
                ' --test',
                # ' --capture-log',
                # ' --no-csv',
                # ' --hide-droplet-history',
                # ' --not-interactive',
                # ' --input-dir ', '/Volumes/Large_Backup/mask_evaluaton_video_samples/Video_data_from__Low-cost_measurement_of_facemask_efficacy/data/files/0002_Set02/',
                ' --input-dir ', '~/Desktop/git/python/fmva/test_source_video',
                # ' --input-dir ', '/Users/CS255/Desktop/git/python/fmva/tmp_fleece_test',
                ' --output-dir ', '/Users/CS255/Desktop/git/python/fmva/tmp_output_3',
                # ' --output-dir ', '/Users/CS255/Desktop/git/python/fmva/tmp_n95_test/output',
                # ' --output-dir ', '/Users/CS255/Desktop/git/python/fmva/tmp_fleece_test/output',
                # ' --no-video-output',
                # ' --no-audio',
                ' --apply-corrections',
                # ' --output-frames ', '4',
                ' --show-video',
                # fmt: on
            ]
        )

    else:
        TEST_ARGS = None

    return TEST_ARGS


def get_options(TEST_ARGS=None):
    # construct the argument parser and parse the arguments

    parser = argparse.ArgumentParser()

    # fmt: off
    group0 = parser.add_argument_group('Input/Output')

    group0.add_argument('-f', '--file', required=False,
                        nargs='+', dest='video_files', metavar='<file name>',
                        help='video files to analyze, either absolute or relative paths')
    group0.add_argument('-o', '--output-dir', metavar='<output directory>',
                        dest='output_directory', action='store', default=None,
                        help='directory for all file output (optional; default will create "output" in video source dir)')
    group0.add_argument('-i', '--input-dir', metavar='<input directory>',
                        dest='input_directory', action='store', default=None,
                        help='video source directory (optional; default is user\'s home directory)')

    group1 = parser.add_argument_group('Droplet Detection')

    group1.add_argument('-t', '--threshold', metavar='<detection threshold>',
                        dest='threshold', type=int, action='store', default=62,
                        help='droplet detection threshold; default=62')
    group1.add_argument('-b', '--border', metavar='<border width>',
                        dest='border', type=int, action='store', default=20,
                        help='width of border region of frame to ignore, in pixels; default=20')
    group1.add_argument('--distance-threshold', metavar='<distance threshold>',
                        dest='distance_threshold', type=int, action='store', default=40,
                        help='absolute distance threshold; greater than overrides similarity; default=40')
    group1.add_argument('--droplet-similarity', metavar='<similarity threshold>',
                        dest='droplet_similarity', type=int, action='store', default=30,
                        help='droplet similarity threshold; smaller is more similar; default=30')
    group1.add_argument('--frame-history', metavar='<frame history>',
                        dest='frame_history', type=int, action='store', default=1,
                        help='number of frames to consider for prior droplet similarity; default=1')
    group1.add_argument('--top-10',
                        dest='TOP_10', action='store_true', default=False,
                        help='generate image files for the top 10 frames by droplet count')

    group2 = parser.add_argument_group('Output Options')

    group2.add_argument('--no-csv', # Note reversed flag.
                        dest='CSV', action='store_false', default=True,
                        help="don't create a .csv data file")
    group2.add_argument('-c', '--no-video-output', # Note reversed flag.
                        dest='CAPTURE_VIDEO', action='store_false', default=True,
                        help="don't create a new video file with annotation")
    group2.add_argument('-l', '--capture-log',
                        dest='LOG', action='store_true', default=False,
                        help='create an HTML log file')
    group2.add_argument('-q', '--quiet', # Note reversed flag.
                        dest='VERBOSE', action='store_false', default=True,
                        help='suppress console window output')
    group2.add_argument('--show-video',  # Note reversed flag.
                        dest='HIDE_VIDEO', action='store_false', default=True,
                        help='show video preview image while processing file')
    group2.add_argument('-n', '--not-interactive',  # Note reversed flag.
                        dest='INTERACTIVE', action='store_false', default=True,
                        help='do not require keyboard interaction to advance to next frame')

    group3 = parser.add_argument_group('Advanced')

    group3.add_argument('--apply-corrections',
                        dest='CORRECTIONS', action='store_true', default=False,
                        help='apply droplet corrections from file <video_source>.corrections')
    group3.add_argument('--hide-droplet-history',
                        dest='HIDE_DROPLET_HISTORY', action='store_true', default=False,
                        help='hide historical droplet outlines for chained droplets in video output')
    group3.add_argument('--output-frames', metavar='<output frames>',
                        dest='output_frames', type=int, action='store', default=1,
                        help='number of frames to duplicate for each source frame')
    group3.add_argument('--no-audio',  # Note reversed flag.
                        dest='INCLUDE_AUDIO', action='store_false', default=True,
                        help='Do *not* copy source audio to annotated video output file')
    group3.add_argument('-d', '--debug',
                        dest='DEBUG', action='store_true', default=False,
                        help='Print debug output to the terminal window')
    group3.add_argument('--test',
                        dest='TEST', action='store_true', default=False,
                        help='Ignore command line parameters and read them from utils.cl_args.get_test_args()')

    # fmt: on

    if TEST_ARGS:
        args = parser.parse_args(TEST_ARGS.split())
    else:
        args = parser.parse_args()
        # Sleight of hand to use test args from get_test_args()
        # if the --test flag is used from the command line.
        if args.TEST is True:
            TEST_ARGS = get_test_args(TEST=True)
            args = parser.parse_args(TEST_ARGS.split())

    return args
