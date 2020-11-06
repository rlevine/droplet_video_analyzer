import cv2
from utils.video import measure_text_size, draw_text
from config.common import dark_green
from config.common import dark_amber
from config.common import amber
from config.common import magenta
from config.common import graph_axis_font


class Grapher:
    """
    Class to draw small pixel graphs.
    TODO Document this.
    TODO This currently draws a two-axis graph and a separate audio graph.
    TODO It'd be interesting to break out graph types, and make it reuseable,
    TODO but we'd start to reimplement ski-kit and boil an ocean we don't need.
    """

    def __init__(
        self,
        origin,
        x_label=None,
        lower_x_label=None,
        y_label=None,
        y2_label=None,
        max_y_data=None,
        max_y2_data=None,
        y_axis_height=None,
    ):
        self.canvas = None
        self.origin = origin
        self.x, self.y = self.origin
        self.value_1_values = []
        self.value_2_values = []
        self.value_3_values = []
        self.value_3_scale = 30  # I've given up on generalizing at this point. :)
        self.x_label = x_label
        self.lower_x_label = lower_x_label
        self.y_label = y_label
        self.y2_label = y2_label
        self.axis_color = dark_green
        self.data_color_1 = amber
        self.data_color_2 = magenta
        self.data_color_3 = dark_amber
        self._x_axis_length = 0
        self._max_data_label_width = 0
        self._max_data_label_height = 0
        self.y1_max = max_y_data  # Max Y data value
        self.y2_max = max_y2_data  # Max Y data value
        self.y_axis_height = y_axis_height  # Pixel height of Y axis

    def update(self, value_1, value_3):
        self.value_1_values.append(value_1)
        self.value_2_values.append(sum(self.value_1_values))
        self.value_3_values.append(int(value_3 * self.value_3_scale))

    def reset_max_y(self, max_y1_data):
        self.y1_max = max_y1_data

    def draw_graph(self):

        self._max_data_label_width, self._max_data_label_height = measure_text_size(
            self.canvas, self.y1_max, graph_axis_font
        )

        # I'm assuming for now that I don't have to scale the on-screen graph
        # horizontally, so one frame gets one pixel on the x axis.
        # This will break on files longer than about 60 seconds of video for
        # 1920x1080 files.

        y1_scaling_factor = self.y_axis_height / self.y1_max
        y2_scaling_factor = self.y_axis_height / self.y2_max

        # y axis
        self.canvas = cv2.line(
            self.canvas,
            self.origin,
            (self.x, self.y - self.y_axis_height),
            self.axis_color,
            1,
        )

        # y axis label
        self.canvas = draw_text(
            self.canvas,
            (self.x - self._max_data_label_width - 13, self.y - 20),
            self.y_label,
            fill=self.axis_color,
            font=graph_axis_font,
            angle=90,
        )
        # x axis label
        self.canvas = draw_text(
            self.canvas,
            (self.x + 20, self.y + 15),
            self.x_label,
            fill=self.axis_color,
            font=graph_axis_font,
        )
        # lower x axis label
        self.canvas = draw_text(
            self.canvas,
            (self.x + 20, self.y + 80),
            self.lower_x_label,
            fill=self.axis_color,
            font=graph_axis_font,
        )
        # y axis max annotation
        self.canvas = draw_text(
            self.canvas,
            (self.x - self._max_data_label_width - 5, self.y - self.y_axis_height - 11),
            str(self.y1_max),
            fill=self.data_color_1,
            font=graph_axis_font,
        )

        # data 1 - droplets per frame
        data_x = self.x + 2
        data_y = self.y - 2
        value_1_count = 1
        for value_1 in self.value_1_values:
            if value_1 > 0:
                self.canvas = cv2.line(
                    self.canvas,
                    (data_x, data_y),
                    (data_x, data_y - int(value_1 * y1_scaling_factor)),
                    self.data_color_1,
                    1,
                )

            self._draw_x_axis(value_1_count)
            if value_1_count % 30 == 0:
                self._draw_second_tick(data_x)
            value_1_count += 1
            data_x += 1

        # data 2 - cumulative - plot after per/frame data, so it appears over.
        data_x = self.x + 2
        data_y = self.y - 2
        value_2_count = 1
        for value_2 in self.value_2_values:
            if value_2 > 0:
                self.canvas = cv2.line(
                    self.canvas,
                    (data_x, data_y - int(value_2 * y2_scaling_factor + 1)),
                    (data_x, data_y - int(value_2 * y2_scaling_factor)),
                    self.data_color_2,
                    1,
                )

            value_2_count += 1
            data_x += 1

        # data 3 - audio data.
        data_x = self.x + 2
        data_y = self.y + 40 + self.value_3_scale
        value_3_count = 1
        for value_3 in self.value_3_values:
            if value_3 > 0:
                self.canvas = cv2.line(
                    self.canvas,
                    (data_x, data_y),
                    (data_x, data_y - value_3),
                    self.data_color_3,
                    1,
                )

            value_3_count += 1
            data_x += 1

        self._draw_right_y_axis()

        return self.canvas

    # Private

    def _draw_x_axis(self, data_count):
        if data_count <= 90:
            self._x_axis_length = 100
        else:
            self._x_axis_length = 10 + data_count

        self.canvas = cv2.line(
            self.canvas,
            self.origin,
            (self.x + self._x_axis_length, self.y),
            self.axis_color,
            1,
        )

    def _draw_second_tick(self, tick_x):

        self.canvas = cv2.line(
            self.canvas, (tick_x, self.y + 5), (tick_x, self.y + 10), self.axis_color, 1
        )

    def _draw_right_y_axis(self):
        #     # y axis
        #     self.canvas = cv2.line(
        #         self.canvas,
        #         self.origin,
        #         (self._x_axis_length + 10, self.y - self.y_axis_height),
        #         self.axis_color,
        #         1,
        #     )

        # y axis right label
        self.canvas = draw_text(
            self.canvas,
            (
                self.x - self._max_data_label_width + 31 + self._x_axis_length + 10,
                self.y - self.y_axis_height + 15,
            ),
            self.y2_label,
            # fill=self.data_color_2,
            fill=self.axis_color,
            font=graph_axis_font,
            angle=270,
        )

        # y axis right max annotation
        self.canvas = draw_text(
            self.canvas,
            (
                self.x - self._max_data_label_width + 25 + self._x_axis_length,
                self.y - self.y_axis_height - 11,
            ),
            str(self.y2_max),
            fill=self.data_color_2,
            font=graph_axis_font,
        )
