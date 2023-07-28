from typing import Dict
from flask import Flask
from threading import Lock


class EnvironmentApplication:
    """
    This class is intended to be used only by gui4us internals
    (for jupyter notebook interface create a custom View).
    """

    def __init__(self, cfg_path: str):
        pass

    def run(self):
        # TODO consider to
        pass


class Application:

    def __init__(self, port: int = 7777, is_debug: bool = False):
        self.app = Flask(Application.__qualname__)
        self.port = port
        self.is_debug = is_debug
        self._envs: Dict[int, EnvironmentApplication] = dict()
        self._state_lock = Lock()
        self._set_routes()

    def run(self):
        self.app.run(port=self.port, debug=self.is_debug)

    def _set_routes(self):
        @self.app.route("/env/{id}")
        def view_env(id: int):
            return self.view_env(id)

        @self.app.route("/env/create")
        def create_env(cfg_path: str):
            return self.create_env(cfg_path)

        @self.app.route("/env/{id}/delete")
        def delete_env(id: int):
            return self.delete_env(id)

        @self.app.route("/env/{id}/capture")
        def capture_env(id: int):
            return self.capture_env(id)

        @self.app.route("/env/{id}/restart")
        def restart_env(id: int):
            return self.restart_env(id)

    def create_env(self, cfg_path: str):
        with self._state_lock:
            # Check if there is env 1: if so, stop it.
            # create EnvironmentApplication with given configuration path
            # start it

            pass

    def view_env(self, id: int):
        with self._state_lock:
            pass

    def delete_env(self, id: int):
        with self._state_lock:
            pass

    def capture_env(self, id: int):
        with self._state_lock:
            pass

    def restart_env(self, id: int):
        with self._state_lock:
            pass
