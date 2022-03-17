from dataclasses import dataclass, field
import threading
import queue
import logging

_LOGGER = logging.getLogger("Controller")


class Event:
    pass


@dataclass(frozen=True)
class MethodCallEvent(Event):
    name: str
    args: tuple = field(default_factory=list)
    kwargs: dict = field(default_factory=dict)


@dataclass(frozen=True)
class CloseEvent:
    pass


class Task:
    def __init__(self, event):
        self.event = event
        self.completed = threading.Event()
        self.result = queue.Queue(maxsize=1)
        self.error = queue.Queue(maxsize=1)

    def wait(self, timeout=None):
        self.completed.wait(timeout)

    def set_ready(self):
        self.completed.set()

    def set_result(self, value):
        self.result.put(value)

    def set_error(self, exc):
        self.error.put(exc)

    def get_result(self):
        self.wait()
        try:
            return self.result.get(block=False)
        except queue.Empty:
            return None

    def get_error(self):
        self.wait()
        try:
            return self.error.get(block=False)
        except queue.Empty:
            return None


class Promise:
    def __init__(self, task):
        self.task = task
        self.result = queue.Queue(maxsize=1)

    def wait(self):
        self.task.wait()

    def get_result(self):
        self.task.get_result()

    def get_error(self):
        self.task.get_error()


class Controller:
    def __init__(self, model):
        self.model = model
        self.task_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.event_queue_runner = threading.Thread(target=self._main_loop)
        self.output_buffers = {}
        for key, output in self.model.outputs.items():
            queue = queue.Queue()
            output.add_callback(lambda data: queue.put(data))
            self.output_buffers[key] = queue

    def send(self, event):
        task = Task(event)
        promise = Promise(task)
        self.task_queue.put(task)
        return promise

    def __getattribute__(self, name):
        if not hasattr(self, name):

            def method(*args, **kwargs):
                return self.send(MethodCallEvent(name, args=args,
                                                 kwargs=kwargs))

            self.__setattr__(name, method)
            return method
        else:
            return object.__getattribute__(self, name)

    def set_setting(self, key, value):
        self.send(MethodCallEvent(f"set_{key}", value))

    def get_output(self, key):
        return self.output_buffers[key]

    def start(self):
        self.event_queue_runner.start()
        self.task_queue.put(MethodCallEvent("start"))

    def close(self):
        self.task_queue.put(CloseEvent())

    def _main_loop(self):
        while True:
            task = None
            try:
                task = self.task_queue.get()
                event = task.event
                if isinstance(event, CloseEvent):
                    self.model.close()
                    return
                result = self.model.__getattribute__(task.name)(*task.args,
                                                                **task.kwargs)
                task.set_result(result)
                task.set_ready()
            except Exception as e:
                logging.exception(e)
                task.set_error(e)
                task.set_ready()


