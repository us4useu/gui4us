from typing import Callable

import panel as pn
from gui4us.logging import get_logger


class ActionsPanel(pn.viewable.Viewer):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.logger = get_logger(type(self))
        self._start_stop_button = pn.widgets.Button(
            name="Start",
            sizing_mode="stretch_width",
            button_type="primary"
        )
        self._capture_button = pn.widgets.Button(name="Capture", sizing_mode="stretch_width")
        self._layout = pn.Column(
            self._start_stop_button,
            self._capture_button
        )

    def __panel__(self) -> pn.viewable.Viewable:
        return self._layout

    def set_start_stop_button_callback(
            self, start_callback: Callable, stop_callback: Callable):
        def internal_callback():
            try:
                if self._start_stop_button.name == "Start":
                    start_callback()
                    self._start_stop_button.name = "Stop"
                else:
                    stop_callback()
                    self._start_stop_button.name = "Start"
            except Exception as e:
                self.logger.error("Exception while pressing start/stop button")
                self.logger.exception(e)
