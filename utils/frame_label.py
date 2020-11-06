import cv2

from config.common import dark_green, medium_gray, orange
from utils.common import ess
from frame.Frame import frames2timecode


def add_frame_header_text(
    display_frame,
    video_file_name_base,
    display_frame_number,
    total_frame_count,
    frame_droplets,
    frame_area,
    total_droplets,
    video_total_unprocessed_droplet_count,
    total_area,
    threshold,
    history,
    similarity,
    distance,
):

    (text_x, text_y) = (50, 50)
    text_string = "{}".format(video_file_name_base)
    ((width, height), baseline) = cv2.getTextSize(
        text_string, cv2.FONT_HERSHEY_PLAIN, 2, 1
    )
    cv2.putText(
        display_frame,
        text_string,
        (text_x, text_y),
        fontFace=cv2.FONT_HERSHEY_PLAIN,
        fontScale=2,
        thickness=1,
        color=dark_green,
    )

    text_y += baseline
    text_string = "Frame {} of {} ({})".format(
        display_frame_number,
        total_frame_count,
        frames2timecode(display_frame_number - 1),
    )
    ((width, height), baseline) = cv2.getTextSize(
        text_string, cv2.FONT_HERSHEY_PLAIN, 2, 1
    )
    text_y += height
    cv2.putText(
        display_frame,
        text_string,
        (text_x, text_y),
        fontFace=cv2.FONT_HERSHEY_PLAIN,
        fontScale=2,
        thickness=1,
        color=dark_green,
    )

    text_y += baseline
    text_string = "Frame: {} new droplet{}, {} pixel{}".format(
        frame_droplets, ess(frame_droplets), frame_area, ess(frame_area)
    )
    ((width, height), baseline) = cv2.getTextSize(
        text_string, cv2.FONT_HERSHEY_PLAIN, 1, 1
    )
    text_y += height
    cv2.putText(
        display_frame,
        text_string,
        (text_x, text_y),
        fontFace=cv2.FONT_HERSHEY_PLAIN,
        fontScale=1,
        thickness=1,
        color=dark_green,
    )

    text_y += baseline
    text_string = "Total: {} unique droplet{}, {} pixel{} ({} raw droplet{})".format(
        total_droplets,
        ess(total_droplets),
        total_area,
        ess(total_area),
        video_total_unprocessed_droplet_count,
        ess(video_total_unprocessed_droplet_count),
    )
    ((width, height), baseline) = cv2.getTextSize(
        text_string, cv2.FONT_HERSHEY_PLAIN, 1, 1
    )
    text_y += height
    cv2.putText(
        display_frame,
        text_string,
        (text_x, text_y),
        fontFace=cv2.FONT_HERSHEY_PLAIN,
        fontScale=1,
        thickness=1,
        color=dark_green,
    )

    text_y += baseline * 2
    text_string = "Brightness threshold: {}/255".format(threshold)
    ((width, height), baseline) = cv2.getTextSize(
        text_string, cv2.FONT_HERSHEY_PLAIN, 1, 1
    )
    text_y += height
    cv2.putText(
        display_frame,
        text_string,
        (text_x, text_y),
        fontFace=cv2.FONT_HERSHEY_PLAIN,
        fontScale=1,
        thickness=1,
        color=dark_green,
    )

    text_y += baseline
    text_string = "Similarity threshold: {}, frame memory {}".format(
        similarity, history
    )
    ((width, height), baseline) = cv2.getTextSize(
        text_string, cv2.FONT_HERSHEY_PLAIN, 1, 1
    )
    text_y += height
    cv2.putText(
        display_frame,
        text_string,
        (text_x, text_y),
        fontFace=cv2.FONT_HERSHEY_PLAIN,
        fontScale=1,
        thickness=1,
        color=dark_green,
    )

    text_y += baseline
    text_string = "Distance threshold: less than or equal to {} pixels".format(distance)
    ((width, height), baseline) = cv2.getTextSize(
        text_string, cv2.FONT_HERSHEY_PLAIN, 1, 1
    )
    text_y += height
    cv2.putText(
        display_frame,
        text_string,
        (text_x, text_y),
        fontFace=cv2.FONT_HERSHEY_PLAIN,
        fontScale=1,
        thickness=1,
        color=dark_green,
    )

    return display_frame


def add_ui_prompt(display_frame, INTERACTIVE=False, BACK_DISABLED=False):

    (text_x, text_y) = (50, 1050)
    if INTERACTIVE:
        text_string = "esc or 'q' to quit, 'c' to capture this frame as a .png, 1-99 to advance more than one frame, any other key to advance one frame"
    else:
        # We're showing the video, but it's not going to pause after each frame,
        # so all they can do is quit.
        text_string = "esc or 'q' to quit"

    cv2.putText(
        display_frame,
        text_string,
        (text_x, text_y),
        fontFace=cv2.FONT_HERSHEY_PLAIN,
        fontScale=1,
        thickness=1,
        color=medium_gray,
    )

    if BACK_DISABLED and INTERACTIVE:
        (text_x, text_y) = (1400, 1050)
        text_string = 'Creating video file or .csv: going backwards is disabled.'
        cv2.putText(
            display_frame,
            text_string,
            (text_x, text_y),
            fontFace=cv2.FONT_HERSHEY_PLAIN,
            fontScale=1,
            thickness=1,
            color=orange,
        )

    return display_frame
