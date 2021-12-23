from gui4us.view.widgets import *
from gui4us.state_graph import *
from gui4us.view.common import *
import numpy as np

# Supported file extensions
_FILE_EXTENSIONS = ";;".join([
    "Python pickle dataset (*.pkl)",
    # "MATLAB file (*.mat)"
])


class CaptureBufferComponent(Panel):

    def __init__(self, controller, title="Buffer"):
        super().__init__(title)
        self.controller = controller
        # Action buttons
        self.capture_button = PushButton("Capture")
        self.save_button = PushButton("Save")
        self.state_label = Label("Press capture ...")
        self.add_component(self.capture_button)
        self.add_component(self.save_button)
        self.add_component(self.state_label)
        self.capture_button.on_pressed(self.__on_capture_button_press)
        self.save_button.on_pressed(self.__on_save_button_press)

        self.save_button.disable()

        self.state_graph = StateGraph(
            states={
                State("empty"),
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
                Transition("capturing", "capture", "captured",
                           self.on_capture_start),  # Reset capture buffer
                Transition("capturing", "capture_done", "captured",
                           self.on_capture_end),
                Transition("captured", "capture", "capturing",
                           self.on_capture_start),
                Transition("captured", "save", "empty",
                           self.on_save)
            }
        )
        self.state = StateGraphIterator(
            self.state_graph, start_state="empty")
        self.buffer_state_output = self.controller.get_output(
            "capture_buffer_events")
        self.thread = QThread()
        self.worker = ViewWorker(self.update)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.is_started = False

    def start(self):
        self.is_started = True
        self.thread.start(priority=QThread.TimeCriticalPriority)

    def stop(self):
        self.is_started = False

    def update(self):
        try:
            event = self.buffer_state_output.get()
            if event is None:
                # event buffer closed
                return
            else:
                capture_size, is_done = event
                if is_done:
                    self.state_label.set_text(f"Done, captured: {capture_size}")
                    self.state.do("capture_done")
                else:
                    self.state_label.set_text(f"Captured frame {capture_size}")
        except Exception as e:
            print(e)

    def __on_capture_button_press(self):
        self.state.do("capture")

    def __on_save_button_press(self):
        self.state.do("save")

    def on_capture_reset(self):
        # TODO
        pass

    def on_capture_start(self, event):
        self.capture_button.enable()
        self.save_button.disable()
        self.controller.start_capture()
        # TODO label z info o zbieraniu danych
        # self.statusBar().showMessage("Capturing RF frames...")

    def on_capture_end(self, event):
        self.save_button.enable()
        # TODO label informing about the data acquisition

    def on_save(self, event):
        # TODO stop acquisition?
        filename, extension = QFileDialog.getSaveFileName(
            parent=None, caption="Save File", directory=".",
            filter=_FILE_EXTENSIONS)
        if extension == "":
            event.stop()
            return
        self.controller.save_capture(filename)
