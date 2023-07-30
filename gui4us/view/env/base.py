import signal
import logging
from abc import ABC, abstractmethod
from typing import Optional, Union
import panel as pn
from bokeh.client import pull_session
from bokeh.embed import server_session
from panel.io.server import StoppableThread

Viewable = Union[pn.viewable.Viewable, pn.template.BaseTemplate]


class AbstractPanelView(ABC):

    def __init__(
            self,
            title: str,
            app_url: str,
            address: Optional[str] = None
    ):
        """
        :param app_url: parent (app) application address; this is the
            allowed websocket origin (shold be hostname:port)
        :param address: websocket server address (should be hostname)
        """
        self.title = title
        self.env_view = self._create_viewable()
        self.template = pn.template.GoldenTemplate(
            title="GUI4us",
            busy_indicator=None,
            header_background="gray",
            header_color="black",
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
        print(f"Starting view server: {self.title}, "
                     f"address: {self.address}, "
                     f"port: {self.server.port}")
        self.server.start()
        try:
            self.server.io_loop.start()
        except RuntimeError:
            pass
        except TypeError:
            print(
                "IOLoop couldn't be started. Ensure it is started by "
                "process invoking the panel.io.server.serve."
            )
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
        print(f"Getting script for url: {url}")
        with pull_session(url=url) as session:
            return server_session(session_id=session.id, url=url)

    def servable(self):
        return self.template

    @abstractmethod
    def _create_viewable(self) -> Viewable:
        pass
