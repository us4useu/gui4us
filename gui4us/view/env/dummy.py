from typing import Optional
import panel as pn
import numpy as np

from gui4us.view.env.base import AbstractPanelView, Viewable


class DummyView(AbstractPanelView):

    def __init__(self,
                 title: str,
                 app_url: str,
                 address: Optional[str] = None):
        super().__init__(
            title=title,
            app_url=app_url,
            address=address,
            # Force environment selection
            dialog_closable=False,
            dialog_autostart=True
        )

    def _create_viewable(self) -> Viewable:
        return pn.Row(
            pn.Column("**Test1**"),
            pn.Column("**Test2**")
        )



