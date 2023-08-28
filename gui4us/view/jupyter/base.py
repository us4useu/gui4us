from gui4us.controller import (
    EnvironmentController
)
from gui4us.view.env import (
    EnvironmentView
)
from gui4us.logging import get_logger
from enum import Enum, auto
from dataclasses import dataclass, field
import threading

# TODO(pjarosik) duplicates gui4us.view.env logic
_DEFAULT_TIMEOUT = 60


class StateId(Enum):
    CREATED = auto()
    RUNNING = auto()
    CLOSED = auto()


class ActionId(Enum):
    RUN = auto()
    CLOSE = auto()
    GET_VIEW_PORT = auto()
    GET_VIEW_SCRIPT = auto()
    GET_VIEW_URL = auto()


@dataclass(frozen=True)
class Event:
    id: Enum
    kwargs: dict = field(default_factory=dict)


class JupyterController:
    def __init__(self, cfg_path: str, address):
        self.logger = get_logger(f"{type(self)}_{id}")
        self.cfg_path = cfg_path
        self.env: EnvironmentController = EnvironmentController(
            id=f"env_{id}",
            env_cfg_path=self.cfg_path
        )
        self.view: EnvironmentView = EnvironmentView(
            title="Jupyter notebook",
            app_url=None,
            address=address,
            cfg_path=self.cfg_path,
            env=self.env,
        )

    def run(self):
        self.logger.info(f"Starting new controller.")
        self.env.run()
        self.view.run()
        self.logger.info(f"App controller for {self.env}, {self.view} started.")
        self.logger.info("Waiting for view and environment to stop.")

    def get_view_script(self):
        return self.view.run()


