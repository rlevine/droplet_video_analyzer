import sys
import cv2
import time
from PIL import Image
from PIL import ImageDraw
import numpy as np

from config.common import bright_red, amber, white, black

# from video.Video import Video

###


def calculate_fps(start_time, end_time, frames):
    """

    Calculates frames per second to be used in friendly console messages.

    :param start_time: time.time() integer seconds
    :param end_time: time.time() integer seconds
    :param frames: number of video frames in the time interval
    :return float fps
    """
    elapsed_seconds = end_time - start_time

    fps = frames / elapsed_seconds

    return fps


def box_the_droplet(display_frame, droplet, color=bright_red, margin=5):
    """
    Draw a box around a contour, using the specified BGR color, and with specified pixel
    margin. Default margin is 5px larger than contour bounding-box, so it doesn't hide
    the edges. Bright red is the default color.

    :param np video frame:
    :param contour: OpenCV contour
    :param color: tuple, BGR color tuple
    :return: np video frame
    """
    box_x, box_y, box_w, box_h = cv2.boundingRect(droplet.contour)
    box_point_1 = tuple([box_x - margin, box_y - margin])
    box_point_2 = tuple([box_x + box_w + margin, box_y + box_h + margin])
    cv2.rectangle(display_frame, box_point_1, box_point_2, color=color, thickness=1)
    # return display_frame, box_x, box_y, box_w, margin
    return display_frame, box_point_1, box_point_2


def draw_text(
    np_image, xy, text, fill=(255, 2555, 255, 255), font=None, angle=0, antialias=True
):
    """
    Use PIL image library to draw text on a numpy image.
    Converts an opencv np image to a PIL canvas and back again.
    xy position is upper left corner of right-reading text
    Function expects a BGR color, and it will be translated to RGB for drawing.
    BGRA is acceptable for transparent text, 0-255 alpha range.

    :param np_image: numpy image to which text will be added
    :param xy: origin xy tuple
    :param text: text to write
    :param fill: BGR or BGRA color tuple
    :param font: PIL ImageFont font name from config/general.py
    :param angle: rotation angle for text - only 90 degree increments right now
    :param antialias: antialias flag, boolean

    :return: np image with added text, with the same number of channels as the input image
    """

    width, height, depth = np_image.shape

    # Add an alpha channel if the image doesn't have one
    ALPHA_CHANNEL_ADDED = False
    if depth == 3:
        ALPHA_CHANNEL_ADDED = True
        np_image = add_alpha_channel(np_image)

    # Flip the color information to RGB.
    # (This isn't really needed, as PIL will ignore the color order: it doesn't know
    # that our color value_1_values are BGR. However, it makes debugging easier if I peek at
    # an intermediate stage of the process and red is red. :)
    np_image[:, :, [0, 1, 2]] = np_image[:, :, [2, 1, 0]]

    # max_dimension = max(width, height)

    # Add alpha for full opacity to supplied color if it doesn't already have an alpha value.
    if len(fill) == 3:
        BGRA_color = fill + (255,)
    else:
        BGRA_color = fill

    # Flip the requested text fill color to RGBA as opencv uses BGRA.
    (b, g, r, a) = BGRA_color
    RGBA_color = (r, g, b, a)

    # Make a PIL image from the supplied opencv image.
    _imagepil = Image.fromarray(np_image)

    # base = Image.open(image.convert("RGBA")

    # Create a new image to draw text on.
    text_image = Image.new("RGBA", _imagepil.size, (255, 255, 255, 0))

    # build a transparency mask large enough to hold the text
    # canvas_size = (max_dimension * 2, max_dimension * 2)
    # text_canvas = Image.new("RGBA", pil_image.size, (0, 0, 0, 0))

    # Create a drawing context on the PIL image...
    draw = ImageDraw.Draw(text_image)

    # This is an undocumented hack in the PIL code to turn off font antialiasing.
    if not antialias:
        draw.fontmode = "1"

    # .. and draw the text.
    draw.text(xy, text, fill=RGBA_color, font=font)

    if angle % 90 == 0:
        # rotate by multiple of 90 deg is easier
        text_image = text_image.rotate(angle, center=xy)
    else:
        # For now, we're just doing multiples of 90 degrees.
        # To do odd angles, we'll need to scale up/scale down the text to smooth jaggies.
        pass

    # Notes here are random fodder for arbitrary rotation

    # # rotate an an enlarged mask to minimize jaggies
    # bigger_canvas = text_image.resize((max_dim*8, max_dim*8),
    #                           resample=Image.BICUBIC)
    # rotated_canvas = text_image.rotate(angle).resize(
    #     canvas_size, resample=Image.LANCZOS)
    #
    # # crop the mask to match image
    # canvas_xy = (max_dimension - xy[0], max_dimension - xy[1])
    # bounding_box = canvas_xy + (canvas_xy[0] + width, canvas_xy[1] + height)
    # canvas = rotated_canvas.crop(bounding_box)

    # paste the appropriate color, with the text transparency mask
    # color_image = Image.new('RGBA', (width, height), RGBA_color)
    # pil_image.paste(canvas)

    # Composite the text on top of the base image.
    composited_image = Image.alpha_composite(_imagepil, text_image)

    # composited_image.show() # Debug

    # Back to a numpy image.
    np_output_image = np.array(composited_image)

    # Remove the alpha channel if we added one.
    if ALPHA_CHANNEL_ADDED:
        remove_alpha_channel(np_output_image)

    # And flip RGB back to BGR
    np_output_image[:, :, [0, 1, 2]] = np_output_image[:, :, [2, 1, 0]]
    # Note that this preserves the alpha channel data, whereas
    #   np_output_image = np_output_image[:,:,[2,1,0]]
    # does not.

    return np_output_image


def measure_text_size(np_image, text, font=None):
    """
    Wrapper for PIL text size function.
    """

    pil_image = Image.fromarray(np_image)
    draw = ImageDraw.Draw(pil_image)

    return draw.textsize(str(text), font)


def threshold_and_find_droplets(frame, threshold, border_width=None, DROPLET_SCAN=True):
    """
    Find all the droplets in a video frame.

    :param frame: np video frame image
    :param threshold: int from 1-254 to use as a brightness threshold
    :param border_width: int width of border frame to blank, to eliminate edge light scatter

    :return: np array of found droplet contours
    :return: grayscale image after thresholding
    """

    # Convert the image to grayscale.
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Block out the border to reduce false positives
    bordered_gray_frame = recolor_border(gray_frame, border_width)

    # Threshold to lose light scatter in image.
    thresholded_frame = threshold_image(bordered_gray_frame, threshold)

    if DROPLET_SCAN:
        # Find the droplets.
        droplets = cv2.findContours(
            thresholded_frame,
            mode=cv2.RETR_EXTERNAL,
            # method=cv2.CHAIN_APPROX_SIMPLE)[-2]
            method=cv2.CHAIN_APPROX_NONE,
        )[-2]

        return droplets, thresholded_frame
    else:
        return thresholded_frame


def threshold_image(source_image, threshold_value):
    """
    Removes all value_1_values in a grayscale image with value_1_values less than supplied threshold.

    :param source_image: grayscale np video frame image
    :param threshold_value: int vaue from 1-254 to use in thresholding

    :return: thresholded np array video frame
    """
    if len(source_image.shape) > 2:
        sys.exit(
            "\nOops. threshold_image wants a grayscale image, not one with a bit depth of {}.\n".format(
                source_image.shape[2]
            )
        )

    _, thresholded_frame = cv2.threshold(
        source_image, threshold_value, 255, cv2.THRESH_BINARY
    )

    return thresholded_frame


def recolor_border(source_image, border_width, border_color=(0, 0, 0)):
    """
    Recolors the border of an image. Default border color is black.

    :param source_image: np array video image
    :param border_width: width of border to recolor
    :param border_color: bgr color tuple, color to apply to border

    :return: np image with border in requested color
    """

    height, width = source_image.shape[:2]
    bw = border_width

    # Rectangle drawing in opencv sucks: corners are rounded, and the line width
    # straddles the dimension line. So we'll slice the data to crop the image
    # and then add a black border.
    bordered_image = source_image[bw : height - bw, bw : width - bw]
    bordered_image = cv2.copyMakeBorder(
        bordered_image, bw, bw, bw, bw, cv2.BORDER_CONSTANT, value=border_color
    )

    return bordered_image


def aggressive_droplet_frame(source_frame, droplets, more_droplets):

    droplet_frame = source_frame.copy()

    # Convert frame back to color so we can write in color on it.
    droplet_frame = cv2.cvtColor(droplet_frame, cv2.COLOR_GRAY2RGB)
    total_optimistic_area = 0
    total_conservative_area = 0

    h, w = droplet_frame.shape[:2]
    mask = np.zeros((h + 2, w + 2), np.uint8)

    flood_connectivity = 8
    optimistic_floodfill_flags = flood_connectivity | cv2.FLOODFILL_FIXED_RANGE

    # Color in aggressive droplet set, which will also catch original droplets.
    for droplet in more_droplets:
        mask[:] = 0
        seed_point = tuple(droplet[0][0])
        area = cv2.floodFill(
            droplet_frame,
            mask,
            seed_point,
            amber,
            (20,) * 3,
            (20,) * 3,
            optimistic_floodfill_flags,
        )[0]
        total_optimistic_area += area

    # Fill original droplets with black, leaving only aggressive additions.
    for droplet in droplets.contour:
        mask[:] = 0
        seed_point = tuple(droplet[0])
        area = cv2.floodFill(
            droplet_frame,
            mask,
            seed_point,
            black,
            (20,) * 3,
            (20,) * 3,
            optimistic_floodfill_flags,
        )[0]
        total_conservative_area += area

    # cv2.imwrite('./saved_colorized_aggressive_image.png', droplet_frame) #Debug

    return droplet_frame, total_optimistic_area - total_conservative_area

    # gained_area = total_optimistic_area - total_area


def add_alpha_channel(source_image, transparent_color=None):
    """
    Add an alpha channel to a numpy image, if it doesn't already have one.

    If supplied an optional BGR color, change all pixels in the image with that color
    value to completely transparent, for example, making all the black areas in an image
    transparent, in preparation for compositing.

    :param source_image: np array video frame
    :param transparent_color: int value for alpha channel pixels, 0-255
    :return: 4-channel np image
    """
    height, width, depth = source_image.shape  # image dimensions

    if depth == 3:
        # Add the alpha channel. Channel value_1_values are 0 to 255, transparent to opaque.
        # If there are already 4 channels, we don't need to add one.
        # (And if there are only 1 or 2 channels, don't do anything unpredictable.)
        alpha_image = np.concatenate(
            [source_image, np.full((height, width, 1), 255, dtype=np.uint8)], axis=-1
        )
    else:
        alpha_image = source_image

    if transparent_color:
        # create a mask with all pixels matching the supplied transparent color
        alpha_mask = np.all(source_image == transparent_color, axis=-1)
        # change the alpha channel value_1_values to 0 (transparent) for all those pixels
        alpha_image[alpha_mask, -1] = 0

    return alpha_image


def remove_alpha_channel(source_image):
    """
    Remove the alpha channel from a numpy image, if it has one. Returns the
    unmodified image if it's only BGR and not BGRA.

    :param source_image: np source image
    :return: BGR np image
    """
    height, width, depth = source_image.shape  # image dimensions

    if depth == 4:
        # Remove the alpha channel.
        # If there is no alpha channel, we don't need to remove it.
        image_without_alpha = source_image[:, :, :3]

    return image_without_alpha


###
