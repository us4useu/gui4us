from typing import Callable

import panel as pn
import logging
from gui4us.view.env.actions import ActionsPanel
from gui4us.view.env.settings import SettingsPanel

logger = logging.getLogger(__name__)


class ControlPanel(pn.viewable.Viewer):

    def __init__(self, env_controller, **kwargs):
        super().__init__(**kwargs)
        self._actions_panel = ActionsPanel(name="Actions")
        accordion_stylsheet = """
        .mdc-card, .accordion, .bk-panel-models-layout-Card {
          box-shadow: none;
          border: none;
        }
        """
        self._layout = pn.Accordion(
            self._actions_panel,
            SettingsPanel(name="Settings", controller=env_controller),
            toggle=False,
            sizing_mode="stretch_both",
            active=[0, 1],
            styles={"box-shadow": "none", "border": "none"},
            stylesheets=[accordion_stylsheet],
        )

    def __panel__(self) -> pn.viewable.Viewable:
        return self._layout

    def set_start_stop_button_callback(
            self, start_callback: Callable, stop_callback: Callable):
        self._actions_panel.set_start_stop_button_callback(
            start_callback=start_callback,
            stop_callback=stop_callback
        )


class EnvironmentSelector(pn.viewable.Viewer):

    def __init__(self, **params):
        self._content = "**Test value**"
        super().__init__(**params)
        self._layout = pn.Row(self._content)

    def __panel__(self) -> pn.viewable.Viewable:
        return self._layout


class ConsoleLog(pn.viewable.Viewer):

    def __init__(self, **params):
        self._content = pn.widgets.Debugger(
            sizing_mode="stretch_both",
            level=logging.DEBUG,
            logger_names=[__name__]
        )
        super().__init__(**params)
        self._layout = pn.Row(self._content)
        logger.info("Starting...")

    def __panel__(self) -> pn.viewable.Viewable:
        return self._layout

