import logging
import sys
import signal
from dataclasses import dataclass
from bokeh.client import pull_session
from bokeh.embed import server_session

from gui4us.controller import EnvController
from gui4us.controller.app import *
from gui4us.view.impl.qt.control import *
from gui4us.cfg.display import *
import panel as pn


class View:
    def __init__(
            self,
            title: str,
            cfg_path: str,
            env: EnvController,
            address: Optional[str] = None
    ):
        super().__init__()
        self.cfg = load_cfg(os.path.join(cfg_path, "display.py"), "display")
        self.view_cfg = self.cfg.VIEW_CFG
        self.title = title
        self.env = env
        self.template = self._create_template()

        # Set server
        self.server: pn.io.server.Server = pn.serve(
            self.template.servable(),
            port=0,  # OS should choose port automatically
            address=address,
            websocket_origin=address,
            show=False,
            title=title,
            threaded=False,
            start=False  # Don't start the application here, it will be started
                         # in the run method.
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
        # TODO is it sufficient?
        # TODO sould it be run on a separate thread?
        logging.info(f"Starting view server: {self.title}, "
                     f"address: {self.address}, "
                     f"port: {self.port}")
        self.server.start()
        try:
            self.server.io_loop.start()
        except RuntimeError:
            pass
        except TypeError:
            logging.warning(
                "IOLoop couldn't be started. Ensure it is started by "
                "process invoking the panel.io.server.serve."
            )

    def close(self):
        # TODO is it sufficient?
        self.server.io_loop.stop()
        self.server.stop()

    def servable(self):
        return self.template

    @property
    def port(self) -> int:
        return self.server.port

    @property
    def address(self) -> str:
        return self.server.address

    @property
    def script(self) -> str:
        with pull_session(url=f"http://{self.address}:{self.port}/") as session:
            return server_session(
                session_id=session.id,
                url=f"http://{self.address}:{self.port}"
            )

    def _create_template(self) -> pn.Template:
        pass
