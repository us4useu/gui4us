import signal
import logging
from abc import ABC, abstractmethod
from typing import Optional, Union
import panel as pn
from bokeh.client import pull_session
from bokeh.embed import server_session


Viewable = Union[pn.viewable.Viewable, pn.template.BaseTemplate]


class AbstractPanelView(ABC):

    def __init__(
            self,
            title: str,
            address: Optional[str] = None
    ):
        self.title = title
        self.env_view = self._create_viewable()
        self.template = pn.template.GoldenTemplate(
            title="GUI4us",
            busy_indicator=False,
            header_background="gray",
            header="black",
            sidebar=[]
        )
        self.template.main.append(
            self.env_view
        )
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
        logging.info(f"Starting view server: {self.title}, "
                     f"address: {self.address}, "
                     f"port: {self.server.port}")
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

    def servable(self):
        return self.template

    @abstractmethod
    def _create_viewable(self) -> Viewable:
        pass
