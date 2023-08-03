import os
import pathlib
from typing import Dict
from flask import Flask, redirect, request, render_template
from threading import Lock
from gui4us.view.app.env import EnvironmentApplication
from gui4us.version import __version__
import gui4us.utils

DEFAULT_APP_HOST = "127.0.0.1"


def get_url(host, port, is_secure=False):
    address = f"{host if host is not None else DEFAULT_APP_HOST}:{port}"
    if is_secure:
        return f"https://{address}"
    else:
        return f"http://{address}"


class Application:
    NULL_VIEW_ID = 0
    MAIN_VIEW_ID = 1

    def __init__(
            self,
            host: str = None,
            port: int = 7777,
            is_debug: bool = False
    ):
        self.app = Flask(
            Application.__qualname__,
            static_url_path="/static",
            static_folder=os.path.join(
                gui4us.utils.get_gui4us_location(),
                "static"
            ),
            template_folder=os.path.join(
                gui4us.utils.get_gui4us_location(),
                "templates"
            )
        )
        self.port = port
        self.is_debug = is_debug
        self._null_env: EnvironmentApplication = EnvironmentApplication(
            id=Application.NULL_VIEW_ID,
            title=f"Welcome to GUI4us {__version__}",
            cfg_path=None,
            address=host,
            app_url=get_url(host, port)
        )
        self._envs: Dict[int, EnvironmentApplication] = dict()
        self._state_lock = Lock()
        self._set_routes()
        self._null_env.run()

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

        @self.app.route("/env/create", methods=["GET"])
        def view_create_env_form():
            return self.view_create_env_form()

        @self.app.route("/env/create", methods=["POST"])
        def create_env():
            cfg_path = request.form.get("cfg_path")
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

        @self.app.route("/favicon.ico")
        def redirect_to_icon():
            return redirect("/static/img/favicon.ico")

    def display_main_view(self):
        with self._state_lock:
            if Application.MAIN_VIEW_ID in self._envs:
                return redirect(f"/env/{Application.MAIN_VIEW_ID}")
            else:
                # Redirect user to the "dummy view"
                return redirect("/env/create")

    def view_env(self, env_id: int):
        with self._state_lock:
            pass

    def view_create_env_form(self):
        with self._state_lock:
            self._null_env.get_view_port()
            view_url = self._null_env.get_view_url()
            return render_template(
"view.html",
                view_url=view_url,
                template="Flask"
            )

    def create_env(self, cfg_path: str):
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
