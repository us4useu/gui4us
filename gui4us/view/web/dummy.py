from typing import Optional

import panel as pn

from gui4us.view.web.base import AbstractPanelView, Viewable


class DummyView(AbstractPanelView):

    def __init__(self, title: str, address: Optional[str] = None):
        super().__init__(title, address)
        self.template.modal.append(
            "This is gui4us!"
        )

    def _create_viewable(self) -> Viewable:
        return pn.Row(
            pn.Card("Test1"),
            pn.Card("Test2")
        )



