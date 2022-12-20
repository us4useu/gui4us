import queue
import threading


class CaptureBuffer:
    def __init__(self, capacity):
        self.capacity = capacity
        self._counter = 0
        self._data = [None]*self.capacity
        self._lock = threading.Lock()

    def append(self, data):
        with self._lock:
            if self.is_ready():
                raise queue.Full()
            self._data[self._counter] = data
            self._counter += 1

    def is_ready(self):
        return self.capacity == self._counter

    def get_current_size(self):
        return self._counter

    @property
    def data(self):
        with self._lock:
            return self._data
