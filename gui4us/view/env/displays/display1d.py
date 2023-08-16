import panel as pn


class Display1D(pn.viewable.Viewer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._layout = pn.Row(self._content)

    def __panel__(self) -> pn.viewable.Viewable:
        return self._layout