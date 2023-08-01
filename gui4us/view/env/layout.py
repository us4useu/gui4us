import pathlib

import panel as pn
import param
import gui4us.version


class GUI4usLayout(pn.template.Template):
    dialog_open = param.Action()
    dialog_close = param.Action()

    TEMPLATE = pathlib.Path(__file__).parent / "templates" / "layout.html"

    def __init__(
            self,
            app_url: str,
            control_panel,
            displays,
            envs,
            console,
            dialog,
            dialog_title: str,
            dialog_autostart: bool,
            dialog_closable: bool
    ):
        super().__init__(
            template=GUI4usLayout.TEMPLATE.read_text(),
        )
        self.add_panel("header", self.get_header(
            app_url,
        ))
        self.add_panel("control_panel", control_panel)
        for i, (k, display) in enumerate(displays.items()):
            self.add_panel(f"display{i}", display)

        self.add_panel("envs", envs)
        self.add_panel("console", console)

        # Dialog
        self.add_panel("dialog", dialog)
        self.add_variable("dialog_title", dialog_title)
        self.add_variable("dialog_autostart", dialog_autostart)
        self.add_variable("dialog_closable", dialog_closable)

    def get_header(self, base_url: str):
        return pn.Row(
            pn.pane.PNG(
                f"{base_url}/static/img/logo.svg",
                height=40,
                margin=10,
                link_url=base_url,
            ),
            styles={"background": "White"},
            sizing_mode="stretch_width",
        )
