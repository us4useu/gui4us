import panel as pn


class SettingsPanel(pn.viewable.Viewer):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        widgets = [pn.pane.Markdown("**Voltage [V]**")]
        widgets.append(
            pn.widgets.IntInput(value=5, step=5, start=5, stop=90)
        )
        widgets.append(pn.pane.Markdown("**TGC [dB]**"))
        for i in range(5):
            slider = pn.widgets.EditableFloatSlider(
            name=f"{i*10} [mm]", start=14, end=54, step=0.1, value=34)
            widgets.append(slider)
        self._layout = pn.Column(
            *widgets,
            sizing_mode="stretch_both"
        )

    def __panel__(self) -> pn.viewable.Viewable:
        return self._layout