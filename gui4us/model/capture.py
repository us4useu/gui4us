import multiprocessing
import queue
import pickle
import scipy.io
import dataclasses
import json
import numpy as np
import h5py


class CaptureBuffer:
    def __init__(self, capacity):
        self.capacity = capacity
        self._counter = 0
        self._data = [None] * self.capacity

    def append(self, data):
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
        return self._data


class Capturer:
    # TODO a separate process (?)
    def __init__(self, capacity, capture_buffer_events, event_frequency=5):
        self.is_capturing = False
        self.capacity = capacity
        self.capture_buffer = CaptureBuffer(capacity)
        self.capture_buffer_events = capture_buffer_events
        self.event_frequency = min(event_frequency, self.capacity)

    def set_metadata(self, metadata):
        self.metadata = metadata

    def append(self, data):
        if self.is_capturing:
            self.capture_buffer.append(data)
            if self.capture_buffer.is_ready():
                self.stop_capture()
            elif self.capture_buffer.get_current_size() % self.event_frequency == 0:
                self.capture_buffer_events.put(
                    (self.capture_buffer.get_current_size(), False))

    def start_capture(self):
        self.capture_buffer = CaptureBuffer(self.capacity)
        self.is_capturing = True

    def clear_capture(self):
        self.is_capturing = False

    def stop_capture(self):
        """
        Stop manually capturing data.
        """
        self.is_capturing = False
        self.capture_buffer_events.put((self.capture_buffer.get_current_size(), True))

    def save_capture(self, filepath):
        if self.capture_buffer.get_current_size() == 0:
            raise ValueError("Cannot save empty buffer")
        # Pickle
        pickle.dump({"metadata": self.metadata,
                     "data": self.capture_buffer.data},
                    open(f"{filepath}.pkl", "wb"))
        print(f"Saved data to {filepath}.pkl")
        # Json with metadata
        result_json = {}
        result_json["pitch"] = self.metadata[0].context.device.probe.model.pitch
        result_json["n_elements"] = self.metadata[0].context.device.probe.model.n_elements
        result_json["sampling_frequency"] = self.metadata[0].context.device.sampling_frequency
        # # HDF5
        with h5py.File(f"{filepath}.h5", "w") as hdf:
            self.data_lists = zip(*self.capture_buffer.data)
            for i, dl in enumerate(self.data_lists):
                hdf.create_dataset(f"output_{i}", data=np.stack(dl))
            hdf.attrs.update(result_json)
        print(f"Saved data to {filepath}.h5")





