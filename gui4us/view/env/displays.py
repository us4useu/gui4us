import threading
import time

import panel as pn
import holoviews as hv
import param
import matplotlib.pyplot as plt

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


class MatplotlibFigure(param.Parameterized):

    def __init__(self, images, **params):
        super(MatplotlibFigure, self).__init__(**params)
        self.images = images
        self.fig, self.ax = plt.subplots()
        self.mpl = pn.pane.Matplotlib(self.fig)
        self.ax.autoscale()
        self.i = 0

    def trigger(self):
        self.ax.imshow(self.images[self.i])
        self.i = (self.i+1)%200
        self.mpl.param.trigger('object')

    def panel(self):
        return pn.Column(self.param, self.mpl)


def _create_test_data():
    images = []
    empty = np.zeros((250, 160), dtype=np.uint8)
    radius = 20

    for i in range(200):
        # Draw the circle at the new position
        y0 = 100
        x0 = i
        y, x = np.ogrid[-y0:250 - y0, -x0:160 - x0]
        mask = x ** 2 + y ** 2 <= radius ** 2
        img = empty.copy()
        img[mask] = 1
        images.append(img)
    images = np.stack(images)
    return images


class Display2D(pn.viewable.Viewer):
    def __init__(self, **params):
        self.images = _create_test_data()
        self._content = MatplotlibFigure(self.images)
        super().__init__(**params)
        self._layout = pn.Row(
            self._content.panel(),
             sizing_mode="stretch_both"
        )
        self.t = threading.Thread(target=self.update)
        self.t.start()
        print("DONE")

    def __panel__(self) -> pn.viewable.Viewable:
        return self._layout

    def update(self):
        time.sleep(5)
        while True:
            self._content.trigger()
            time.sleep(0.1)


class Display3D(pn.viewable.Viewer):

    def __init__(self, **params):
        self._content = pn.pane.PNG(
            "http://localhost:7777/static/img/image_placeholder.png")
        super().__init__(**params)
        self._layout = pn.Row(self._content)

    def __panel__(self) -> pn.viewable.Viewable:
        return self._layout