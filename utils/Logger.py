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

import sys
from ansi2html import Ansi2HTMLConverter


class Transcript(object):
    """
    Quick adaptation of code to duplicate sys.stdout to a log file and instead
    tee to a list which is then fed to Ansi2HTMLConverter to make a colored HTML
    transcript file of the console output.
    """

    # source: https://stackoverflow.com/q/616645

    def __init__(self, filename="tmp.html", mode="a", buff=0):
        self.stdout = sys.stdout
        # self.file = open(filename, mode, buff)
        self.lines = []
        self.transcript = open(filename, mode="w")

        self.conv = Ansi2HTMLConverter()

        sys.stdout = self

    def __del__(self):
        self.transcript.close()

    def __enter__(self):
        pass

    def __exit__(self, *args):
        self.close()

    def write(self, message):
        self.stdout.write(message)
        # self.file.write(message)
        self.lines.append(message)

    def flush(self):
        self.stdout.flush()
        # self.file.flush()
        # os.fsync(self.file.fileno())

    def close(self):
        if self.stdout is not None:
            sys.stdout = self.stdout
            self.stdout = None

        # if self.file != None:
        #     self.file.close()
        #     self.file = None

        self.conv.scheme = "mint-terminal"
        self.transcript.write(self.conv.convert("".join(self.lines)))
        self.transcript.close()
