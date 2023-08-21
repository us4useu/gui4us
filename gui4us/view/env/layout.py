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
        self.display_rows = self._split_displays_to_rows(displays, n_cols=2)
        self.add_variable("display_rows", self.display_rows)
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

    def _split_displays_to_rows(self, displays, n_cols):
        result = []
        # TODO(pjarosik) currently simply sort by display id,
        # allow any custom layout in the future
        displays = list(displays.items())
        sorted(list(displays), key=lambda x: x[0])
        displays = [p[1] for p in displays]
        n_displays = len(displays)
        n_rows = n_displays // n_cols
        if n_rows * n_cols < len(displays):
            n_rows += 1
        for r in range(n_rows):
            row = []
            for c in range(n_cols):
                i = r*n_cols + c
                if i < len(displays):
                    row.append(displays[i])
                else:
                    row.append(None)
            result.append(row)
        return result

