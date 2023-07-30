from gui4us.controller.base import AbstractController


class DummyController(AbstractController):
    """
    Dummy controller -- no actions is performed here.
    This controller is intended to be sued in companion with the
    DummyView.
    """

    def close(self):
        pass

    def run(self):
        pass
