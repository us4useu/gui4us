import panel as pn


class ActionsPanel(pn.viewable.Viewer):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._layout = pn.Column(
            pn.widgets.Button(
                name="Next",
                sizing_mode="stretch_width",
                button_type="primary"
            ),
            pn.widgets.Button(name="Previous", sizing_mode="stretch_width"),
        )

    def __panel__(self) -> pn.viewable.Viewable:
        return self._layout