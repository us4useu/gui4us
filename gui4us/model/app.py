from gui4us.model.core import *


class App:
    """
    Main app model.
    """

    def __init__(self):
        self.envs = {}

    def add_env(self, cfg) -> Env:
        pass

    def remove_env(self, id: EnvId):
        pass

    def close(self):
        """
        Closes all open environments.
        """
        pass
