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


class Dispatcher:
    """
    Dispatcher for video processing behaviors.
    """

    def __init__(
        self,
        interactive=False,
        capture_video=False,
        hide_video=False,
        top_10=False,
        csv=False,
    ):

        self._INTERACTIVE = interactive
        self._CAPTURE_VIDEO = capture_video
        self._HIDE_VIDEO = hide_video
        self._TOP_10 = top_10
        self._CSV = csv

        self._dispatch_dict = {
            'back': self._action_back,
            'next': self._action_next,  # param: number of frames
            'reprocess': self._action_reprocess,  # param: threshold
            'redisplay': self._action_redisplay,
            'capture': self._action_capture,  # (and then action redisplay)
            'stop': self._action_stop,
            'threshold_up': self._action_threshold_up,  # (and then action reprocess)
            'threshold_down': self._action_threshold_down,  # (and then action reprocess)
        }

    def _filter_command(self, action):

        # Short circuit all the fun stuff if we're saving
        # stats or creating a video file, because messing with
        # frame order or changing the video threshold will mess
        # them up. And if we're not interactive, it doesn't matter.
        if not self._INTERACTIVE or self._TOP_10 or self._CSV or self._CAPTURE_VIDEO:
            if action not in ('next', 'stop', 'capture'):
                action = 'next'
        return action

    def dispatch(self, action):
        action = self._filter_command(action)
        return self._dispatch_dict[action]

    def _action_capture(self, frame_processor):
        return frame_processor.capture_current_frame()

    def _action_back(self, frame_processor):
        return frame_processor.previous_frame()

    def _action_next(self, frame_processor):
        return frame_processor.next_frame()

    def _action_reprocess(self, frame_processor, new_threshold):
        frame_processor.video_threshold = new_threshold
        return frame_processor.reprocess_last_frame()

    def _action_threshold_up(self, frame_processor):
        frame_processor.image_threshold_up()
        return frame_processor.reprocess_last_frame()

    def _action_threshold_down(self, frame_processor):
        frame_processor.image_threshold_down()
        return frame_processor.reprocess_last_frame()

    def _action_redisplay(self, frame_processor):
        return frame_processor.processed_frame

    def _action_stop(self, frame_processor):
        return None
