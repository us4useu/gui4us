from typing import Dict
from flask import Flask, redirect
from threading import Lock
from gui4us.app.env import EnvironmentApplication


class Application:
    MAIN_VIEW_ID = 1

    def __init__(self, port: int = 7777, is_debug: bool = False):
        self.app = Flask(Application.__qualname__)
        self.port = port
        self.is_debug = is_debug
        self._null_env: EnvironmentApplication = EnvironmentApplication()
        self._envs: Dict[int, EnvironmentApplication] = dict()
        self._state_lock = Lock()
        self._set_routes()

    def run(self):
        self.app.run(port=self.port, debug=self.is_debug)

    def close(self):
        """
        Closes all environments and cleanups this instance.
        """
        for k, env in self._envs:
            env.close()

    def _set_routes(self):
        @self.app.route("/")
        def main():
            return self.display_main_view()

        @self.app.route("/env/<env_id>")
        def view_env(env_id: int):
            return self.view_env(env_id)

        @self.app.route("/env/create")
        def view_create_env_form():
            return self.view_create_env_form()

        @self.app.route("/env/create")
        def create_env(cfg_path: str):
            return self.create_env(cfg_path)

        @self.app.route("/env/<env_id>/delete")
        def delete_env(env_id: int):
            return self.delete_env(env_id)

        @self.app.route("/env/<env_id>/capture")
        def capture_env(env_id: int):
            return self.capture_env(env_id)

        @self.app.route("/env/<env_id>/restart")
        def restart_env(env_id: int):
            return self.restart_env(env_id)

    def display_main_view(self):
        with self._state_lock:
            if Application.MAIN_VIEW_ID in self._envs:
                redirect(f"/env/{Application.MAIN_VIEW_ID}")
            else:
                # Redirect user to the "dummy view"
                redirect("/env/create")

    def view_env(self, env_id: int):
        with self._state_lock:
            pass

    def view_create_env_form(self):
        with self._state_lock:
            pass

    def create_env(self, cfg_path: str):
        # TODO cfg_path should be passed via
        with self._state_lock:
            # TODO
            # Check if there is env 1: if so, reset it
            # create EnvironmentApplication with given configuration path
            # run it

            # start main
            pass

    def delete_env(self, env_id: int):
        with self._state_lock:
            pass

    def capture_env(self, env_id: int):
        with self._state_lock:
            pass

    def restart_env(self, env_id: int):
        with self._state_lock:
            pass