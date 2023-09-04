import asyncio
from dataclasses import dataclass
from typing import Optional, Sized

from vtkmodules.vtkWebCore import vtkWebApplication
from vtkmodules.web import protocols
from wslink import server
from wslink import websocket


class Gui4usServerProtocol(websocket.ServerProtocol):
    """
    Based on the vtk/wslink.ServerProtocol implementation.
    """

    def __init__(self):
        self.application = None
        self.setSharedObject("app", self.init_application())
        websocket.ServerProtocol.__init__(self)

    def init_application(self):
        self.application = vtkWebApplication()
        return self.application

    def set_application(self, application):
        self.setSharedObject("app", application)

    def get_application(self):
        return self.getSharedObject("app")

    def register_vtk_web_protocol(self, protocol):
        self.registerLinkProtocol(protocol)

    def get_vtk_web_protocols(self):
        return self.getLinkProtocols()


@dataclass(frozen=True)
class VTKDisplayServerOptions:
    host: str = "localhost"
    port: str = "1234"
    debug: bool = False
    reverse_url: str = None
    timeout: Optional[int] = 0
    nows: Optional[object] = None
    content: object = ""
    fsEndpoints: Sized = ()
    ssl: str = ""
    ws: str = ""
    nosignalhandlers: bool = True


class VTKDisplayServerProtocol(Gui4usServerProtocol):
    authKey = "wslink-secret"

    def __init__(self, render_view):
        self.render_view = render_view
        super().__init__()

    def initialize(self):
        self.register_vtk_web_protocol(protocols.vtkWebViewPort())
        self.publish_protocol = protocols.vtkWebPublishImageDelivery(decode=False)
        self.register_vtk_web_protocol(self.publish_protocol)
        self.register_vtk_web_protocol(protocols.vtkWebViewPortGeometryDelivery())
        # TODO fix the below
        # self.register_vtk_web_protocol(protocols.vtkWebMouseHandler())
        # Update authentication key to use
        self.updateSecret(VTKDisplayServerProtocol.authKey)

        self.get_application().SetImageEncoding(0)
        self.get_application().GetObjectIdMap().SetActiveObject("VIEW", self.render_view)
        self.publish_protocol.setMaxFrameRate(fps=100)
        self.publish_protocol.startViewAnimation()


class VTKDisplayServer:

    def __init__(self, render_view, options: VTKDisplayServerOptions):
        self.protocol = lambda: VTKDisplayServerProtocol(
            render_view=render_view)
        self.options = options
        self.main_task = None
        self.main_thread = None
        self.server_loop = asyncio.get_event_loop()  # asyncio.new_event_loop()

    def start(self):
        # NOTE: the below task will run in the current thread (main?)
                # loop.
        # Make sure to wait for all task before exiting this thread.
        old_event_loop = asyncio.get_event_loop()
        try:
            # The below is necessary because asyncio.get_event_loop is
            # used during start_webserver call
            asyncio.set_event_loop(self.server_loop)
            self.coroutine = server.start_webserver(
                options=self.options, protocol=self.protocol,
                exec_mode="coroutine")
        finally:
            # Cleanup
            asyncio.set_event_loop(old_event_loop)
        self.main_task = self.server_loop.create_task(self.coroutine)

    def join(self):
        asyncio.wait(self.main_task)

