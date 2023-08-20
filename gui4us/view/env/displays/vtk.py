from typing import Optional, Sized

import vtk
from abc import abstractmethod
from vtkmodules.web import protocols
from vtkmodules.web import wslink as vtk_wslink
from wslink import server
from threading import RLock

from wslink import websocket
from wslink import register as exportRpc
from vtkmodules.web import protocols
from vtkmodules.vtkWebCore import vtkWebApplication
from dataclasses import dataclass


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
    nosignalhandlers: bool = False


class VTKDisplayServerProtocol(Gui4usServerProtocol):
    authKey = "wslink-secret"

    def __init__(self, render_view):
        self.render_view = render_view
        super().__init__()

    def initialize(self):
        self.register_vtk_web_protocol(protocols.vtkWebViewPort())
        publish_protocol = protocols.vtkWebPublishImageDelivery(decode=False)
        self.register_vtk_web_protocol(publish_protocol)
        self.register_vtk_web_protocol(
            protocols.vtkWebViewPortGeometryDelivery())
        # Update authentication key to use
        self.updateSecret(VTKDisplayServerProtocol.authKey)

        self.get_application().SetImageEncoding(0)
        self.get_application().GetObjectIdMap().SetActiveObject("VIEW",
                                                                self.render_view)


class VTKDisplayServer:

    def __init__(self, render_view, options: VTKDisplayServerOptions):
        self.protocol = lambda: VTKDisplayServerProtocol(
            render_view=render_view)
        self.options = options
        self.main_task = None

    def start(self):
        self.main_task = server.start_webserver(
            options=self.options, protocol=self.protocol,
            exec_mode="task",
        )
        print("STARTED!")
