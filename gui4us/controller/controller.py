import traceback
from dataclasses import dataclass, field
import threading
import queue
import logging
import multiprocessing as mp

import gui4us.cfg
from gui4us.model.model import Environment
from gui4us.model.ultrasound import HardwareEnv
from gui4us.model.dataset import DatasetEnv
from gui4us.model.capture import *
from gui4us.common import *

_LOGGER = logging.getLogger("Controller")


class Event:
    pass


@dataclass(frozen=True)
class MethodCallEvent(Event):
    name: str
    args: tuple = field(default_factory=list)
    kwargs: dict = field(default_factory=dict)


@dataclass(frozen=True)
class CloseEvent(Event):
    name: str = "close"


class Task:
    def __init__(self, event, id: int):
        self.id = id
        self.event = event


class Promise:
    def __init__(self, task):
        self.task = task
        self.completed = threading.Event()
        self.completed.clear()
        self.result = queue.Queue(maxsize=1)
        self.error = queue.Queue(maxsize=1)

    def wait(self, timeout=None):
        # Interface
        self.completed.wait()

    def set_ready(self):
        self.completed.set()

    def set_result(self, value):
        self.result.put(value)

    def set_error(self, exc):
        self.error.put(exc)

    def get_result(self):
        # Interface
        self.wait()
        try:
            result = self.result.get(block=False)
            return result
        except queue.Empty:
            return None

    def get_error(self):
        self.wait()
        try:
            return self.error.get(block=False)
        except queue.Empty:
            return None


class EnvProcess:

    def __init__(self, env_cfg_path):
        self._promises = {}
        self.task_queue = mp.Queue()
        self.result_queue = mp.Queue()
        self.capture_buffer_events = mp.Queue()
        self.data_buffer = DataBuffer(size=4)
        self.task_id_lock = threading.Lock()
        self.current_task_id = 0
        self.result_queue_runner = threading.Thread(target=self._result_handler)
        self.result_queue_runner.start()
        self.event_queue_runner = mp.Process(
            target=_env_controller_main_loop,
            args=(env_cfg_path, self.task_queue, self.result_queue, self.capture_buffer_events,
                  self.data_buffer))
        print("Starting DAQ process")
        self.event_queue_runner.start()
        print("Process started")

    def send(self, event: Event):
        """
        End-point (abstract)
        """
        task = Task(event, self.create_task_id())
        promise = Promise(task)
        self._promises[task.id] = promise
        self.task_queue.put(task)
        return promise

    def close(self):
        self.result_queue.put(None)
        self.event_queue_runner.join()
        self.result_queue_runner.join()

    def create_task_id(self):
        with threading.Lock():
            self.current_task_id += 1
            return self.current_task_id

    def _result_handler(self):
        while True:
            result = self.result_queue.get()
            if result is None:
                # Close
                return
            task_id, result = result
            if id is None:
                return
            promise = self._promises[task_id]
            if isinstance(result, Exception):
                promise.set_error(result)
                promise.set_ready()
            else:
                promise.set_result(result)
                promise.set_ready()


def _env_controller_main_loop(cfg_path, task_queue, result_queue, capture_buffer_events,
                              data_buffer):
    # Puts (None, exc) if exception on initialization
    # Puts (id, result|exc) otherwise
    try:
        import gui4us.cfg
        cfg = gui4us.cfg.load_cfg(cfg_path)
        cfg = cfg.environment
        # Don't wait for the queue to be empty.
        task_queue.cancel_join_thread()
        result_queue.cancel_join_thread()
        capture_buffer_events.cancel_join_thread()
        data_buffer.queue.cancel_join_thread()

        env = None
        if isinstance(cfg, gui4us.cfg.HardwareEnvironment):
            env = HardwareEnv(cfg, data_buffer)
        elif isinstance(cfg, gui4us.cfg.DatasetEnvironment):
            env = DatasetEnv(cfg, data_buffer)
        else:
            raise ValueError(f"Unsupported type of environment: {cfg}")
        # TODO there should probably be a separate process and controller for the capturer
        capturer = Capturer(cfg.capture_buffer_capacity, capture_buffer_events)
        env.set_capturer(capturer)
        capturer_events = {
            "start_capture", "stop_capture", "clear_capture", "save_capture",
            "get_capture_buffer_events"}
    except Exception as e:
        print(e)
        print(traceback.format_exc())
        result_queue.put((None, e))
        return
    while True:
        task = None
        try:
            task = task_queue.get()
            event = task.event
            result = None
            if isinstance(event, CloseEvent):
                result = env.close()
                return
            if event.name in capturer_events:
                result = capturer.__getattribute__(event.name)(*event.args, **event.kwargs)
            else:
                result = env.__getattribute__(event.name)(*event.args, **event.kwargs)
            result = (task.id, result)
            result_queue.put(result)
        except Exception as e:
            print(e)
            print(traceback.format_exc())
            result_queue.put((task.id, e))


class EnvController:
    def __init__(self, env_cfg_path):
        self.process = EnvProcess(env_cfg_path)

    def set_setting(self, key, value):
        # Interface
        return self.process.send(MethodCallEvent(f"set_{key}", value))

    def get_output(self):
        # Interface, returns output data queue buffer.
        return self.process.data_buffer

    def get_output_metadata(self, ordinal):
        return self.process.send(MethodCallEvent(
            "get_output_metadata", kwargs=dict(ordinal=ordinal)))

    def start(self):
        # Interface
        return self.process.send(MethodCallEvent("start"))

    def stop(self):
        return self.process.send(MethodCallEvent("stop"))

    def close(self):
        # Interface
        result = self.process.send(CloseEvent())
        self.process.close()
        return result

    def get_settings(self):
        result = self.process.send(MethodCallEvent("get_settings"))
        return result

    def start_capture(self):
        return self.process.send(MethodCallEvent("start_capture"))

    def stop_capture(self):
        return self.process.send(MethodCallEvent("stop_capture"))

    def save_capture(self, path):
        return self.process.send(MethodCallEvent("save_capture", args=(path, )))

    def clear_capture(self):
        self.process.send(MethodCallEvent("clear_capture"))

    def get_capture_buffer_events(self):
        return self.process.capture_buffer_events


class MainController:

    def __init__(self):
        self.envs = {}

    def open_environment(self, name: str, env_cfg_path):
        env = EnvController(env_cfg_path)
        self.envs[name] = env
        return env

    def get_env(self, name):
        return self.envs[name]

    def close_env(self, name):
        self.envs[name].close()

    def close(self):
        for _, env in self.envs.items():
            env.close()
