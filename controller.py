from model import Model


class Controller:
    def __init__(self, model: Model):
        self.model = model

    @property
    def settings(self):
        return self.model.settings

    def get_bmode(self):
        return self.model.get_bmode()

    def get_rf(self):
        return self.model.get_rf()
