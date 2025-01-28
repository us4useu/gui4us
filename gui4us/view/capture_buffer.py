import pickle

from gui4us.view.widgets import *
from gui4us.view.common import *
import gui4us.controller.app as app
from gui4us.state_graph import *
import numpy as np
import queue
from datetime import datetime

# Supported file extensions
_FILE_EXTENSIONS = ";;".join([
    "Python pickle dataset (*.pkl)",
    # "MATLAB file (*.mat)"
])


class CaptureBuffer:
    def __init__(self, capacity):
        self.capacity = capacity
        self._counter = 0
        self._data = [None]*self.capacity

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


class CaptureBufferComponent(Panel):

    def __init__(self, env: app.EnvController, capture_buffer_capacity: int,
                 title="Buffer"):
        super().__init__(title)
        # TODO
        self.env = env
        # Action buttons
        self.capture_button = PushButton("Capture")
        self.save_button = PushButton("Save")
        self.state_label = Label("Press capture ...")
        self.add_component(self.capture_button)
        self.add_component(self.save_button)
        self.add_component(self.state_label)

        self.capture_button.on_pressed(self._on_capture_button_press)
        self.save_button.on_pressed(self._on_save_button_press)
        self.state_graph = StateGraph(
            states={
                State("empty", on_enter=self.on_empty_buffer),
                State("capturing"),
                State("captured")
            },
            actions={
                Action("capture"),
                Action("capture_done"),
                Action("save")
            },
            transitions={
                Transition("empty", "capture", "capturing",
                           self.on_capture_start),
                Transition("capturing", "capture", "capturing",
                           self.on_capture_start),  # Reset capture buffer
                Transition("capturing", "capture_done", "captured",
                           self.on_capture_end),
                Transition("captured", "save", "empty",
                           self.on_save),
                Transition("captured", "capture", "capturing",
                           self.on_capture_start),
            }
        )
        self.state = StateGraphIterator(
            self.state_graph, start_state="empty")

        self.env.get_stream().append_on_new_data_callback(self.update)
        self.capture_buffer: CaptureBuffer = None
        self.capture_buffer_capacity = capture_buffer_capacity

    def update(self, data):
        try:
            if self.state.is_current_state("capturing"):
                arrays = [np.copy(a) for a in data]
                arrays = tuple(arrays)
                self.capture_buffer.append(arrays)
                self.state_label.set_text(
                    f"Frames: {self.capture_buffer.get_current_size()}"
                )
                if self.capture_buffer.is_ready():
                    self.state.do("capture_done")
        except Exception as e:
            print(e)

    def _on_capture_button_press(self):
        self.state.do("capture")

    def _on_save_button_press(self):
        self.state.do("save")

    def on_capture_start(self, event):
        self.capture_buffer = CaptureBuffer(self.capture_buffer_capacity)
        self.capture_button.enable()
        self.save_button.disable()

    def on_capture_end(self, event):
        self.save_button.enable()

    def on_save(self, event):
        filename, extension = QFileDialog.getSaveFileName(
            parent=None, caption="Save File", directory=".",
            filter=_FILE_EXTENSIONS)
        if extension == "":
            event.stop()
            return
        pickle.dump(self.capture_buffer.data, open(filename, "wb"))

    def on_empty_buffer(self, event):
        self.save_button.disable()
