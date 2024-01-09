import pathlib
import threading
import queue
import os.path
from gui4us.logging import get_logger
from gui4us.controller.event import *
from gui4us.controller.task import *
from gui4us.model import *
from gui4us.utils import load_cfg
from enum import Enum


class EnvController:
    """
    TODO unload configuration after closing this controller
    """

    def __init__(self, id: EnvId, env_cfg_path: str):
        self.logger = get_logger(f"{type(self)}_{id}")
        self.id = id
        self.env_cfg_path = os.path.join(env_cfg_path, "env.py")
        self.env: Env = None
        self.task_queue = queue.Queue()
        self.event_queue_runner = threading.Thread(target=self._main)
        self.env_ready_event = threading.Event()
        self.started_properly = False
        self.event_queue_runner.start()
        self.env_ready_event.wait()
        if not self.started_properly:
            raise ValueError("Env controller didn't started properly, "
                    "please check the other errors for more details.")

        self.logger.info("Environment is ready.")

    def start(self):
        self._send(MethodCallEvent("start"))

    def stop(self):
        self._send(MethodCallEvent("stop"))

    def close(self):
        self._send(CloseEvent())

    def set(self, set_action: SetAction):
        return self._send(MethodCallEvent("set", (set_action, )))

    def get_settings(self) -> Promise:
        return self._send(MethodCallEvent("get_settings"))

    def get_stream(self) -> Stream:
        return self.env.get_stream()

    def get_stream_metadata(self) -> Promise:
        return self._send(MethodCallEvent("get_stream_metadata"))

    def _send(self, event):
        task = Task(event)
        promise = Promise(task)
        self.task_queue.put(task)
        return promise

    def _main(self):
        """
        Creates underlying app model and starts event handler loop.
        """
        try:
            try:
                self.cfg = load_cfg(self.env_cfg_path, self.id)
            except Exception as e:
                self.logger.exception(e)
                self.started_properly = False
                self.env_ready_event.set()  # wake up master thread
                return
            self.env = self.cfg.ENV
            self.started_properly = True
            self.env_ready_event.set()
            self._event_loop()
        finally:
            if self.env is not None:
                self.env.close()
            self.logger.info("Closed.")

    def _event_loop(self):
        while True:
            task = None
            try:
                task = self.task_queue.get()
                event = task.event
                if isinstance(event, CloseEvent):
                    self.logger.debug("Stopping app event loop.")
                    return
                result = self.env.__getattribute__(event.name)(*event.args,
                                                               **event.kwargs)
                task.set_result(result)
                task.set_ready()
            except Exception as e:
                self.logger.exception(e)
                task.set_error(e)
                task.set_ready()
