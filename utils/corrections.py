import re
import os
from utils.common import printc
from utils.common import substitute_tokens, strip_tokens
from droplet_video_analyzer.parts import get_filename_from_path

correction_file_text_template = """# Droplet correction file for video data file:

# %%file_name%%

# The video file was analyzed with these parameter settings:

# video threshold: %%threshold%%
# frame history: %%frame_history%%
# droplet similarity threshold: %%droplet_similarity%%
# droplet distance threshold: %%droplet_distance%%

# THESE CORRECTIONS MAY NOT BE VALID IF THE VIDEO DATA IS PROCESSED WITH OTHER SETTINGS!

# This file is used to correct droplet history assignments when the video data file is evaluated.
# All lines starting with "#" are comments and will be ignored, as will any text after a "#"
# in the middle of a line.

# Blank lines will be ignored, as will any extra whitespace in lines.

# To force a droplet to be ignored when the software is mistakenly identifying it as a repeat
# of a droplet in a prior frame, but the number of that droplet on a line by itself. (Without
# the leading number sign, of course.):

# 34

# To indicate a droplet is a repeat of a prior droplet when it was either not assigned or mistakenly
# assigned to the wrong predecessor, put its number first on a line followed by the number of
# its correct predecessor:

# 34 30

"""


def load_correction_file(correction_file_path):

    droplet_corrections = {}

    correction_file = open(correction_file_path, "r")
    lines = correction_file.readlines()
    correction_file.close()

    correction_count = 0

    for i, line in enumerate(lines):
        if line.strip() == "" or line[0] == "#":
            continue
        else:
            parts = line.split("#")
            matches = re.findall(r"(\d+)", parts[0])
            if len(matches) == 2:
                droplet_corrections[int(matches[0])] = int(matches[1])
                correction_count += 1
            elif len(matches) == 1:
                droplet_corrections[int(matches[0])] = None
                correction_count += 1
            else:
                printc(
                    "\nOops! Correction file line {} isn't something we expected:\n    {}\n".format(
                        i + 1, line
                    ),
                    "red",
                )

    return droplet_corrections, correction_count


def get_correction_file_data(
    correction_file_path=None,
    output_file_path=None,
    video_threshold=None,
    frame_history=None,
    droplet_similarity=None,
    distance_threshold=None,
):
    # If it does exist, load any droplet corrections from the override file.
    if os.path.exists(correction_file_path):
        # Returns dict of droplet corrections and count.
        return load_correction_file(correction_file_path)
    else:
        # if not, create a blank one from the template text.
        correction_file_text_string = strip_tokens(
            substitute_tokens(
                {
                    "filename": get_filename_from_path(output_file_path),
                    "threshold": video_threshold,
                    "frame_history": frame_history,
                    "droplet_similarity": droplet_similarity,
                    "distance_threshold": distance_threshold,
                },
                correction_file_text_template,
            )
        )
        correction_file = open(correction_file_path, "w")
        correction_file.write(correction_file_text_string)
        correction_file.close()

        # And set the empty state variables if we created a new file.
        droplet_corrections = {}
        correction_count = None

        return droplet_corrections, correction_count
