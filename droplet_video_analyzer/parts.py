import cv2
import os
import sys
import re
import datetime
import csv

from utils.frame_label import add_ui_prompt
import config.common as config


def get_video_file_path(video_filename=None, input_directory=None):
    """
    Build an absolute path for the supplied video file name, looking in
    various locations.

    :param video_filename:
    :return: string video_file_path or None if not found.
    """
    current_working_dir = os.getcwd()
    if input_directory:
        default_video_dir = os.path.expanduser(input_directory)
    else:
        # Use their home directory if they haven't told us where to look.
        default_video_dir = os.path.expanduser("~")

    video_file_input_path = None

    if os.path.isfile(video_filename):
        # We already have an absolute path.
        video_file_input_path = video_filename
    elif os.path.isfile(os.path.join(default_video_dir, video_filename)):
        # The file in the default video directory.
        video_file_input_path = os.path.join(default_video_dir, video_filename)
    elif os.path.isfile(os.path.join(current_working_dir, video_filename)):
        # The file in the current working directory.
        video_file_input_path = os.path.join(current_working_dir, video_filename)
    else:
        print("\nOops. Can't find video file {}.\n".format(video_filename))

    return video_file_input_path


def get_file_directory_from_path(file_path):
    return os.path.dirname(file_path)


def get_filename_from_path(file_path):
    return os.path.basename(file_path)


def get_file_root_ext_from_file_name(filename):
    return os.path.splitext(filename)


def set_up_output_filenames(video_file_input_path, argv_output_dir=None):
    # File name set-up for video output file.

    output_files = {}

    video_file_directory = get_file_directory_from_path(video_file_input_path)
    video_filename = get_filename_from_path(video_file_input_path)
    video_filename_root, video_file_ext = get_file_root_ext_from_file_name(
        video_filename
    )

    # If we haven't gotten an output directory, create one in the source dir.
    if argv_output_dir is None:
        output_dir = os.path.join(video_file_directory, 'output')

    # Create the output directory, if it doesn't exist.
    if argv_output_dir:
        output_dir = os.path.expanduser(argv_output_dir)  # Catch tilde naming
        if not os.path.exists(output_dir):
            try:
                os.mkdir(output_dir)
            except Exception as error:
                sys.exit(
                    "\n\nOops. Cannot create specified output directory!\n{}\n{}\n".format(
                        output_dir, error
                    )
                )
    else:
        # If we haven't gotten an output directory, create one in the source dir.
        if argv_output_dir is None:
            output_dir = os.path.join(video_file_directory, 'output')
            if not os.path.exists(output_dir):
                try:
                    os.mkdir(output_dir)
                except Exception as error:
                    sys.exit(
                        "Unable to create directory 'output' in source directory\n{}\n{}".format(
                            video_file_directory, error
                        )
                    )

    # Time string to be added to annotated video file names.
    # Seconds are included to avoid problems when restarting in under a minute,
    # as opencv cv2.VideoWriter seems to want to die rather than overwriting a file.
    # I'm assuming that a date is useful in the file name, rather than
    # just filename_1.mp4, filename_2.mp4, etc.
    video_date = datetime.datetime.now()
    date_string = video_date.strftime("%d%b%Y_%H%M_%S").upper()

    # Assemble output file names.
    video_output_filename = (
        video_filename_root + "_annotated_" + date_string + video_file_ext
    )
    video_with_audio_output_filename = (
        video_filename_root + "_annotated_w_audio_" + date_string + video_file_ext
    )
    log_output_filename = video_filename_root + "_log_" + date_string + ".html"
    csv_output_filename = video_filename_root + "_data_" + date_string + ".csv"
    # Image capture files are intended as temporary one-off files, and aren't
    # date-stamped. They won't be overwritten, as the creation code will
    # keep sequentially numbering them across multiple runs.
    image_capture_filename = video_filename_root + "_image_capture_1.png"

    output_files["video_file_output_path"] = os.path.join(
        output_dir, video_output_filename
    )
    output_files["video_audio_file_output_path"] = os.path.join(
        output_dir, video_with_audio_output_filename
    )
    output_files["log_file_output_path"] = os.path.join(output_dir, log_output_filename)
    output_files["csv_file_output_path"] = os.path.join(output_dir, csv_output_filename)
    output_files["image_capture_file_output_path"] = os.path.join(
        output_dir, image_capture_filename
    )

    correction_filename = video_filename_root + ".corrections"
    output_files["correction_file_path"] = os.path.join(
        video_file_directory, correction_filename
    )

    output_files["top_10_output_file_path"] = os.path.join(
        output_dir,
        video_filename_root + "_top_10_frame_0" + ".png",
    )

    # Save the parts, in case they'll be used elsewhere.
    # (But eventually, well move all uses back to this function.)
    # output_files["video_filename_base"] = video_filename_base
    # output_files["video_filename_root"] = video_filename_root

    # This should be almost impossible to do, but just in case...
    if os.path.exists(output_files["video_file_output_path"]):
        sys.exit("\nOops. You started twice within a second.\nDon't do that.")

    return output_files


def manage_display_and_keyboard(
    display_frame,
    INTERACTIVE=False,
    counting_frame_number=None,
    total_number_of_frames_in_video=None,
    params=None,
):
    """
     Manage the cv2 image display and peculiar keyboard interaction.

    :param display_frame: np video frame to display, sans the UI prompt
    :param INTERACTIVE: flag to allow interactive video display
    :param counting_frame_number: frame number for window header
    :param total_number_of_frames_in_video: total number of frames in iile
    :param frames_to_advance: number of frames left on an auto-advance sequence
    :return: str next action string,
    :return: dict params (currently just params['frames_to_advance'])
    """

    # Do the light show.

    # Add interactive prompt to the displayed video. This will not be on
    # the frame saved to the video file.
    interactive_display_frame = add_ui_prompt(
        display_frame, INTERACTIVE=INTERACTIVE, BACK_DISABLED=params['back_disabled']
    )

    # opencv video display
    cv2.startWindowThread()
    cv2.imshow(
        "Frame {}: {} droplets".format(
            counting_frame_number, total_number_of_frames_in_video
        ),
        interactive_display_frame,
    )

    # Keyboard interaction:

    # dispatcher = {
    #     "back": action_back,
    #     "next": action_next,  # param: number of frames
    #     "reprocess": action_reprocess,  # param: threshold
    #     "redisplay": action_redisplay,
    #     "capture": action_capture,  # (and then action redisplay)
    # }

    # "q" or esc to quit
    # press 0-9 once or twice to advance that many frames
    # any other key to advance a single frame
    if params['frames_to_advance'] > 1:
        # We're in the middle of an auto-advance sequence.
        params['frames_to_advance'] -= 1
        cv2.waitKey(1)
        cv2.destroyAllWindows()
        return 'next', params

    if not INTERACTIVE:
        # Not interactive, only wait long enough, 100msec, to allow quitting.
        key = cv2.waitKey(100) & 0xFF
        if key == ord('q') or key == 27:
            # esc or 'q' to quit

            # print("key = {} (not interactive)".format(key))  # Debug
            cv2.destroyAllWindows()
            return 'stop', params
        else:
            cv2.destroyAllWindows()
            return 'next', params

    # Otherwise, in interactive mode, we wait indefinitely for a keypress.
    key = cv2.waitKey(0) & 0xFF  # Trim to low 8 bits

    # Check any keys pressed.

    # print("key = {}".format(key))  # Debug

    if key == ord('q') or key == 27:
        # esc or 'q' to quit
        cv2.destroyAllWindows()
        return 'stop', params

    elif 48 <= key <= 57:
        # Numeric value_1_values of first key code pressed.
        # If a digit was entered, wait for second digit keypress, if any,
        # and set number of frames to advance.
        frames_to_advance = int(chr(key))
        params['frames_to_advance'] = int(str(frames_to_advance))
        key2 = cv2.waitKey(500)
        if key2 != -1 and (48 <= key2 <= 57):
            # Don't mess up if they type a number and then a letter.
            params['frames_to_advance'] = int(str(frames_to_advance) + chr(key2))
        cv2.destroyAllWindows()
        return 'next', params

    elif key == ord("c"):
        # # Save a screen capture of the current frame to disk.
        # image_capture_file_name_next_count = 1
        # while os.path.exists(image_capture_file_output_path):
        #     image_capture_file_output_path = re.sub(
        #         r"_\d+\.png",
        #         rf"_{str(image_capture_file_name_next_count)}.png",
        #         image_capture_file_output_path,
        #     )
        #     image_capture_file_name_next_count += 1
        # cv2.imwrite(image_capture_file_output_path, display_frame)
        cv2.destroyAllWindows()
        return 'capture', params

    elif key == ord('+') or key == ord('='):
        cv2.destroyAllWindows()
        return 'threshold_up', params
    elif key == ord('-') or key == ord('_'):
        cv2.destroyAllWindows()
        return 'threshold_down', params

    elif key == ord(',') or key == 2:
        cv2.destroyAllWindows()
        return 'back', params

    cv2.destroyAllWindows()
    return 'next', params
