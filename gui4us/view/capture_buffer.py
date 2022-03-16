from gui4us.view.widgets import *
from gui4us.state_graph import *
import numpy as np

# Supported file extensions
_FILE_EXTENSIONS = ";;".join([
    "Numpy file (*.npz)",
    # "MATLAB file (*.mat)"
])


class CaptureBufferComponent(Panel):

    def __init__(self, env, title="Buffer"):
        super().__init__(title)
        self.env = env
        # Action buttons
        self.capture_button = PushButton("Capture")
        self.save_button = PushButton("Save")
        self.add_component(self.capture_button)
        self.add_component(self.save_button)
        self.capture_button.on_pressed(self.__on_capture_button_press)
        self.save_button.on_pressed(self.__on_save_button_press)
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

    def __on_capture_button_press(self):
        self.state.do("capture")

    def __on_save_button_press(self):
        self.state.do("save")

    def on_capture_start(self, event):
        self.capture_button.enable()
        self.save_button.enable()
        self.env.start_capture()
        # self.statusBar().showMessage("Capturing RF frames...")

    def on_capture_end(self, event):
        self.save_button.enable()
        # ViewModel knows, that the data was captured?
        # self.view_model.stop_capture()
        # TODO label informing about the data acquisition
        # self.statusBar().showMessage(
        #     "Capture done, press 'Save' button to save the data to disk.")

    def on_save(self, event):
        # Stop the processing thread, so we know the system is not running
        # if self._current_state == _STARTED:
        #     self._update_graph_state(_STOP)
        filename, extension = QFileDialog.getSaveFileName(
            parent=None, caption="Save File", directory=".",
            filter=_FILE_EXTENSIONS)
        if extension == "":
            event.stop()
            return
        self.env.save_capture(filename)
        # self.statusBar().showMessage(f"Saved file to {filename}. Ready.")
        # Start the processing thread back

        # # if self._current_state == _STOPPED:
        #     self._update_graph_state(_START)
        return True