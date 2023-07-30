from typing import Optional

import panel as pn

from gui4us.view.env.base import AbstractPanelView, Viewable


class DummyView(AbstractPanelView):

    def __init__(self,
                 title: str,
                 app_url: str,
                 address: Optional[str] = None):
        super().__init__(title=title, app_url=app_url, address=address)
        self.template.modal.append(
            "This is gui4us!"
        )

    def _create_viewable(self) -> Viewable:
        return pn.Row(
            pn.Card("Test1"),
            pn.Card("Test2")
        )



