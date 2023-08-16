import numpy as np
import panel as pn





class Display3D(pn.viewable.Viewer):

    def __init__(self, **params):
        self._content = pn.pane.PNG(
            "http://localhost:7777/static/img/image_placeholder.png")
        super().__init__(**params)
        self._layout = pn.Row(self._content)

    def __panel__(self) -> pn.viewable.Viewable:
        return self._layout

