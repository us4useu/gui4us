import panel as pn
import holoviews as hv

import numpy as np

hv.extension("bokeh")

hv.opts.defaults(
   hv.opts.Image(responsive=True, tools=["hover"], cmap="gray"),
)


class Display1D(pn.viewable.Viewer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._layout = pn.Row(self._content)

    def __panel__(self) -> pn.viewable.Viewable:
        return self._layout


class Display2D(pn.viewable.Viewer):
    def __init__(self, frame, **params):
        bounds = (-5, 50, 5, 30)
        self._content = hv.Image(
            frame, bounds=bounds,
            sizing_mode="stretch_height"
        )
        self._content = pn.pane.HoloViews(
            self._content,
            sizing_mode="stretch_both"
        )
        super().__init__(**params)
        self._layout = pn.Row(self._content, sizing_mode="stretch_both")

    def __panel__(self) -> pn.viewable.Viewable:
        return self._layout


class Display3D(pn.viewable.Viewer):

    def __init__(self, **params):
        self._content = pn.pane.PNG(
            "http://localhost:7777/static/img/image_placeholder.png")
        super().__init__(**params)
        self._layout = pn.Row(self._content)

    def __panel__(self) -> pn.viewable.Viewable:
        return self._layout