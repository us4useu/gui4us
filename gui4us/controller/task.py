import threading
import queue


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
