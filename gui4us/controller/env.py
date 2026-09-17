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

    def __init__(self, id: EnvId, env_cfg_path: str = None, env=None):
        """
        :param id: environment id
        :param env_cfg_path: path to the configuration DIRECTORY holding ``env.py``
          (the module is expected to provide an ``ENV`` attribute)
        :param env: an :class:`gui4us.model.Env` instance, or a callable returning one --
          the alternative to ``env_cfg_path`` for scripts (see :class:`gui4us.Gui4us`).
          A callable is invoked on the controller thread, i.e. the thread that will own the
          hardware from then on.
        """
        if (env_cfg_path is None) == (env is None):
            raise ValueError("Provide exactly one of env_cfg_path, env.")
        self.logger = get_logger(f"{type(self)}_{id}")
        self.id = id
        self.env_cfg_path = (os.path.join(env_cfg_path, "env.py")
                             if env_cfg_path is not None else None)
        self._env_source = env
        self.env: Env = None
        self.task_queue = queue.Queue()
        self.event_queue_runner = threading.Thread(target=self._main)
        self.env_ready_event = threading.Event()
        self.started_properly = False
        self._close_sent = False
        self.event_queue_runner.start()
        self.env_ready_event.wait()
        if not self.started_properly:
            raise ValueError("Env controller didn't started properly, "
                    "please check the other errors for more details.")

        self.logger.info("Environment is ready.")
        # The worker thread is deliberately NOT a daemon: the environment (and the hardware) must
        # be closed properly. But Python joins non-daemon threads *before* running atexit
        # handlers, so a script that never calls close() would hang forever at exit with the
        # hardware still running. threading's own pre-join hook closes the environment in time.
        _register_close_at_exit(self.close)

    def start(self) -> Promise:
        # NOTE: the promise is returned so that a caller can wait for the environment to
        # actually start and see the error when it does not (the event loop runs on another
        # thread); the Qt view ignores it, as it did before.
        return self._send(MethodCallEvent("start"))

    def stop(self) -> Promise:
        return self._send(MethodCallEvent("stop"))

    def close(self):
        if self._close_sent:
            return
        self._close_sent = True
        self._send(CloseEvent())

    def set(self, set_action: SetAction) -> Promise:
        return self._send(MethodCallEvent("set", (set_action, )))

    def get_settings(self) -> Promise:
        return self._send(MethodCallEvent("get_settings"))

    def get_stream(self) -> Stream:
        return self.env.get_stream()

    def get_stream_metadata(self) -> Promise:
        return self._send(MethodCallEvent("get_stream_metadata"))

    def call(self, method: str, *args, **kwargs) -> Promise:
        """Calls a method of the underlying environment on the controller thread.

        This is how environment specific operations (e.g. ``set_subsequence`` of the ARRUS
        environment) are invoked without touching the hardware from another thread.
        """
        return self._send(MethodCallEvent(method, args, kwargs))

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
                if self.env_cfg_path is not None:
                    self.cfg = load_cfg(self.env_cfg_path, self.id)
                    self.env = self.cfg.ENV
                elif isinstance(self._env_source, Env):
                    self.env = self._env_source
                elif callable(self._env_source):
                    # Created here, so that the environment (and the hardware it opens)
                    # belongs to this thread.
                    self.env = self._env_source()
                else:
                    raise ValueError(
                        f"env should be an Env instance or a callable returning one, "
                        f"got: {type(self._env_source)}")
            except Exception as e:
                self.logger.exception(e)
                self.started_properly = False
                self.env_ready_event.set()  # wake up master thread
                return
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


def _register_close_at_exit(close):
    """Registers ``close`` to run at interpreter exit, before non-daemon threads are joined.

    ``threading._register_atexit`` (Python >= 3.9) runs its callbacks right before the
    interpreter waits for non-daemon threads -- which is exactly when the environment thread has
    to be told to finish. Falls back to ``atexit`` on older interpreters (where a missing
    ``close()`` can still hang at exit).
    """
    import atexit
    import weakref

    register = getattr(threading, "_register_atexit", None)
    if register is None:
        atexit.register(close)
        return
    # A weak reference, so that registering does not keep closed controllers alive.
    method = weakref.WeakMethod(close)

    def _close():
        bound = method()
        if bound is not None:
            bound()

    try:
        register(_close)
    except RuntimeError:
        # The interpreter is already shutting down.
        atexit.register(close)
