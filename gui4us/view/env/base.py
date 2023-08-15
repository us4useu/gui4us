import os
import signal
import logging
from abc import ABC, abstractmethod
from typing import Optional, Union, Tuple, Dict
import panel as pn
from bokeh.client import pull_session
from bokeh.embed import server_session
from panel.io.server import StoppableThread

from gui4us.view.env.layout import GUI4usLayout
from gui4us.view.env.widgets import FileSelector

from gui4us.logging import get_logger

Viewable = Union[pn.viewable.Viewer, pn.viewable.Viewable, pn.template.BaseTemplate]

js_files = {
    "jquery": "https://code.jquery.com/jquery-1.11.1.min.js",
    "goldenlayout": "https://golden-layout.com/files/latest/js/goldenlayout.min.js"
}
css_files = [
    "https://golden-layout.com/files/latest/css/goldenlayout-base.css",
    "https://golden-layout.com/files/latest/css/goldenlayout-light-theme.css"
]

pn.extension("vtk", "terminal", js_files=js_files, css_files=css_files, design="material")


class AbstractPanelView(ABC):

    def __init__(
            self,
            title: str,
            app_url: str,
            address: Optional[str] = None,
            dialog_autostart=False,
            dialog_closable=True,
    ):
        """
        Abstract class for Holoviz Panel Views.

        :param app_url: parent (app) application address; this is the
            allowed websocket origin (should be hostname:port)
        :param address: websocket server address (should be hostname)
        """
        self.logger = get_logger(f"{type(self)} {title}")
        self.title = title
        self.dialog_title, self.dialog_view = self._create_dialog_view()
        self.template = GUI4usLayout(
            app_url=app_url,
            control_panel=self._create_control_panel(),
            displays=self._create_displays(),
            envs=self._create_envs_panel(),
            console=self._create_console_log_panel(),
            dialog=self.dialog_view,
            dialog_title=self.dialog_title,
            dialog_autostart=dialog_autostart,
            dialog_closable=dialog_closable
        )
        # Set server
        self.server: pn.io.server.Server = pn.serve(
            self.template.servable(),
            port=0,  # OS should choose port automatically
            address=address,
            # allow_websocket_origin=[app_url],
            show=False,
            title=title,
            threaded=False,
            start=False  # Don't start the application here, it will be started
            # in the run method.
        )
        self.server_thread = StoppableThread(
            target=self._run_impl,
            io_loop=self.server.io_loop,
            args=(),
        )

        def sig_exit(*args, **kwargs):
            self.server.io_loop.add_callback_from_signal(do_stop)

        def do_stop(*args, **kwargs):
            self.server.io_loop.stop()

        try:
            signal.signal(signal.SIGINT, sig_exit)
        except ValueError:
            pass  # Can't use signal on a thread

    def run(self):
        self.server_thread.start()

    def _run_impl(self):
        self.logger.info(f"Starting view server: {self.title}, "
              f"address: {self.address}, "
              f"port: {self.server.port}")
        self.server.start()
        try:
            self.server.io_loop.start()
        except RuntimeError as e:
            self.logger.exception(e)
        except TypeError as e:
            self.logger.error(
                "IOLoop couldn't be started. Ensure it is started by "
                "process invoking the panel.io.server.serve."
            )
            self.logger.exception(e)
        finally:
            return self.server

    def close(self):
        # TODO is it sufficient?
        self.server.io_loop.stop()
        self.server.stop()

    @property
    def port(self) -> int:
        return self.server.port

    @property
    def address(self) -> str:
        return self.server.address

    @property
    def url(self):
        # TODO(pjarosik): accessing panel internals, may not compatible with
        # the future releases of panel
        return self.server._absolute_url

    @property
    def script(self) -> str:
        url = self.url
        with pull_session(url=url) as session:
            return server_session(session_id=session.id, url=url)

    def servable(self):
        return self.template

    @abstractmethod
    def _create_control_panel(self) -> Viewable:
        pass

    @abstractmethod
    def _create_displays(self) -> Dict[str, Viewable]:
        pass

    @abstractmethod
    def _create_envs_panel(self) -> Viewable:
        pass

    @abstractmethod
    def _create_console_log_panel(self) -> Viewable:
        pass

    def _create_dialog_view(self) -> Tuple[str, Viewable]:
        """
        Currently this is "Create env" dialog by default, but can be changed
        in the future.
        """
        file_selector = FileSelector(os.getcwd(), name="Select directory")

        env_editor = pn.widgets.CodeEditor(
            value="# start here...",
            sizing_mode="stretch_width",
            language="python", height=300,
            name="Environment"
        )
        display_editor = pn.widgets.CodeEditor(
            value="# start here...",
            sizing_mode="stretch_width",
            language="python", height=300,
            name="Display"
        )

        code_editor = pn.Column(
            env_editor,
            display_editor
        ,
            name="Edit Environment")

        create_env_tabs = pn.Tabs(
            file_selector,
            # code_editor  TODO(pjarosik)
        )
        title = "Select Environment"
        return title, create_env_tabs
