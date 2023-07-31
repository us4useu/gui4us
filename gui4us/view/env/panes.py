import panel as pn
import logging
from gui4us.view.env.actions import ActionsPanel
from gui4us.view.env.settings import SettingsPanel

logger = logging.getLogger(__name__)


class ControlPanel(pn.viewable.Viewer):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._layout = pn.Accordion(
            ActionsPanel(name="Actions"),
            SettingsPanel(name="Settings"),
            toggle=False,
            sizing_mode="stretch_both",
            active=[0, 1]
        )

    def __panel__(self) -> pn.viewable.Viewable:
        return self._layout


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

