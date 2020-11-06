from PIL import ImageFont
import numpy as np

import os

base_dir = "/Users/CS255/Desktop/git/python/fmva"

default_video_dir = "./test_source_video"


# BGR Colors
dark_green = (0, 136, 0)
bright_green = (0, 255, 0)
bright_red = (0, 0, 255)
amber = (4, 152, 251)
# magenta = (252, 3, 202)
magenta = (99, 14, 82)
# dark_amber = (3, 98, 153)
dark_amber = (3, 82, 128)
orange = (3, 125, 255)
black = (0, 0, 0)
white = (255, 255, 255)
medium_gray = (150, 150, 150)
dark_gray = (50, 50, 50)

# Numpy print options
np.set_printoptions(
    precision=2, linewidth=150, suppress=True, sign=" ", floatmode="maxprec_equal"
)

# Fonts
graph_axis_font = ImageFont.truetype(
    os.path.join(base_dir, "fonts/Lato-Regular.ttf"), 14
)

title_font = ImageFont.truetype(
    os.path.join(base_dir, "fonts/century_gothic_bold.ttf"), 249
)

# fmt: off
# footer_font = ImageFont.truetype(os.path.join(base_dir, 'fonts/century_gothic_bold.ttf'), 74)
# heading_font = ImageFont.truetype(os.path.join(base_dir, 'fonts/century_gothic_regular.ttf'), 57)
# param_font = ImageFont.truetype(os.path.join(base_dir, 'fonts/century_gothic_bold.ttf'), 57)
# pick_font = ImageFont.truetype(os.path.join(base_dir, 'fonts/century_gothic_bold.ttf'), 47)
# note_font = ImageFont.truetype(os.path.join(base_dir, 'fonts/century_gothic_bold.ttf'), 36)
#
# small_title_font = ImageFont.truetype(os.path.join(base_dir, 'fonts/chunkfive.ttf'), 72)
# date_font = ImageFont.truetype(os.path.join(base_dir, 'fonts/chunkfive.ttf'), 48)
# other_note_font = ImageFont.truetype(os.path.join(base_dir, 'fonts/chunkfive.ttf'), 36)
# tiny_font = ImageFont.truetype(os.path.join(base_dir, 'fonts/century_gothic_bold.ttf'), 26)
# slightly_tiny_font = ImageFont.truetype(os.path.join(base_dir, 'fonts/century_gothic_bold.ttf'), 36)
# color_font = ImageFont.truetype(os.path.join(base_dir, 'fonts/century_gothic_regular.ttf'), 42)
#
# number_font = ImageFont.truetype(os.path.join(base_dir, 'fonts/arial_rounded_bold.ttf'), 68)
# link_font = ImageFont.truetype(os.path.join(base_dir, 'fonts/arial_rounded_bold.ttf'), 44)
# tiny_number_font = ImageFont.truetype(os.path.join(base_dir, 'fonts/arial_rounded_bold.ttf'), 20)
#
# prefix_font = ImageFont.truetype(os.path.join(FRANKIE_SOURCE_DIR, 'fonts/SourceSansPro-Black.ttf'), 110)
# color_font = ImageFont.truetype(os.path.join(FRANKIE_SOURCE_DIR, 'fonts/SourceSansPro-Bold.ttf'), 110)
# title_font = ImageFont.truetype(os.path.join(FRANKIE_SOURCE_DIR, 'fonts/chunkfive.ttf'), 96)
# small_title_font = ImageFont.truetype(os.path.join(FRANKIE_SOURCE_DIR, 'fonts/chunkfive.ttf'), 72)
# date_font = ImageFont.truetype(os.path.join(FRANKIE_SOURCE_DIR, 'fonts/chunkfive.ttf'), 48)
# note_font = ImageFont.truetype(os.path.join(FRANKIE_SOURCE_DIR, 'fonts/chunkfive.ttf'), 36)
# tiny_font = ImageFont.truetype(os.path.join(FRANKIE_SOURCE_DIR, 'fonts/century_gothic_bold.ttf'), 26)
# fmt: on

###
