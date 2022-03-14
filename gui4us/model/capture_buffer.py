import datetime

class CaptureBuffer:

    def __init__(self, size):
        self.size = size
        self._counter = 0
        self._data = []

    def append(self, data):
        self._data.append(data)
        self._counter += 1

    def is_ready(self):
        return self.size == self._counter

    @property
    def data(self):
        return self._data


class CaptureBufferViewModel:

# TODO decorator, which wraps the method into the action call (via queue)
# TODO this ViewModel will have to have an access to the DisplayViewModel (Environment)
    def start_capture(self):
        self._rf_buffer = None
        # Create new buffer
        self._rf_buffer = CaptureBuffer(self.rf_buffer_size)

    def save(self, filename):
        date_time = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        filename = filename.strip()
        datas, mask, rfs, gain, voltage = zip(*self._rf_buffer.data)
        rfs = np.stack(rfs)
        datas = np.stack(datas)
        mask = np.stack(mask)
        gain = np.stack(gain)
        voltage = np.stack(voltage)
        data = {"time": date_time, "rf": rfs, "bmode": datas, "mask": mask,
                "gain": gain, "voltage": voltage,
                "extent_ox": self.extent_ox, "extent_oz": self.extent_oz,
                "tx_frequency": self._controller.settings["sequence"]["tx_frequency"]}

        self.statusBar().showMessage(f"Saving file to {filename}, please wait...")
        np.savez(filename, **data)
        self._reset_capture_buffer()
