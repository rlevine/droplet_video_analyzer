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

import numpy as np


class PrintArray:
    def __init__(self, **kwargs):
        self._kwargs = kwargs

    def __repr__(self):
        rpr = (
            "PrintArray("
            + ", ".join([f"{name}={value}" for name, value in self._kwargs.items()])
            + ")"
        )
        return rpr

    def __array_ufunc__(self, ufunc, method, *inputs, **kwargs):
        if ufunc != np.floor_divide:
            return NotImplemented
        a = inputs[0]
        with np.printoptions(**self._kwargs):
            print(a)
