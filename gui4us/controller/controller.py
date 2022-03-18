import traceback
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
        self.completed.clear()
        self.result = queue.Queue(maxsize=1)
        self.error = queue.Queue(maxsize=1)

    def wait(self, timeout=None):
        self.completed.wait()

    def set_ready(self):
        self.completed.set()

    def set_result(self, value):
        self.result.put(value)

    def set_error(self, exc):
        self.error.put(exc)

    def get_result(self):
        self.wait()
        try:
            result = self.result.get(block=False)
            # print(f"RESULT: {result}")
            return result
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

    def wait(self):
        self.task.wait()

    def get_result(self):
        result = self.task.get_result()
        return result

    def get_error(self):
        return self.task.get_error()


class OutputWorker:
    def __init__(self):
        self.queue = queue.Queue()

    def put(self, data):
        self.queue.put(data)

    def get(self):
        return self.queue.get()


class Controller:
    def __init__(self, model):
        self.model = model
        self.task_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.event_queue_runner = threading.Thread(target=self._main_loop)
        self.event_queue_runner.start()
        self.output_buffers = {}
        for key, output in self.model.outputs.items():
            worker = OutputWorker()
            output.add_callback(worker.put)
            self.output_buffers[key] = worker

    def send(self, event):
        task = Task(event)
        promise = Promise(task)
        self.task_queue.put(task)
        return promise

    def __getattr__(self, item):
        if item in self.__class__.__dict__:
            return getattr(self, item)
        else:
            def new_method(*args, **kwargs):
                return self.send(MethodCallEvent(item, args=args, kwargs=kwargs))
            setattr(self, item, new_method)
            return getattr(self, item)

    def _default_method_handler(self, name, *args, **kwargs):
        return

    def set_setting(self, key, value):
        self.send(MethodCallEvent(f"set_{key}", value))

    def get_output(self, key):
        return self.output_buffers[key]

    def start(self):
        self.send(MethodCallEvent("start"))

    def close(self):
        self.send(CloseEvent())

    def _main_loop(self):
        while True:
            task = None
            try:
                # print("Controller ready, waiting for new data...")
                task = self.task_queue.get()
                event = task.event
                if isinstance(event, CloseEvent):
                    print("Closing controller")
                    self.model.close()
                    return
                print("EVENT")
                print(event)
                result = self.model.__getattribute__(event.name)(*event.args,
                                                                **event.kwargs)
                task.set_result(result)
                task.set_ready()
            except Exception as e:
                print(e)
                print(traceback.format_exc())
                task.set_error(e)
                task.set_ready()


