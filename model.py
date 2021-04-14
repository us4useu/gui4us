import numpy as np

class DataSource:

    def get(self):
        raise ValueError("NYI")


class CineloopDataSource(DataSource):

    def __init__(self, collection):
        self.collection = collection
        self._counter = 0

    def get(self):
        result = self.collection[self._counter]
        self._counter = (self._counter+1) % len(self.collection)
        return result


class Model:
    def __init__(self):
        pass

    @property
    def settings(self):
        raise ValueError("Abstract class")

    def get_bmode(self):
        raise ValueError("Abstract class")

    def get_rf(self):
        raise ValueError("Abstract class")

    def set_tgc_curve(self, tgc_curve: np.ndarray):
        raise ValueError("Abstract class")

    def set_dr_min(self, dr_min: float):
        raise ValueError("Abstract class")

    def set_dr_max(self, dr_max: float):
        raise ValueError("Abstract class")

    def set_tx_voltage(self, voltage: float):
        raise ValueError("Abstract class")

    def close(self):
        raise ValueError("Abstract class")


def compute_tgc_curve_linear(oz_min, oz_max, tgc_start, tgc_slope,
                             tgc_sampling_step):
    tgc_sampling_depths = np.arange(oz_min, oz_max, step=tgc_sampling_step)
    tgc_curve = tgc_slope*(tgc_sampling_depths-oz_min) + tgc_start
    print(tgc_curve)
    return tgc_sampling_depths, tgc_curve


class MockedModel(Model):

    def __init__(self, lri_data):
        super().__init__()
        self._rf_data = lri_data
        self._rf_data_source = CineloopDataSource(self._rf_data)
        self._bmode_data = np.sum(self._rf_data, axis=1)
        self._bmode_data = 20 * np.log10(np.abs(self._bmode_data))
        self._bmode_data = np.transpose(self._bmode_data, (0, 2, 1))
        self._bmode_data_source = CineloopDataSource(self._bmode_data)

        self._settings = {
            "initial_voltage": 20,  # [V]
            "min_voltage": 5,  # [V]
            "max_voltage": 75,  # [V]
            "initial_min_dynamic_range": 20,  # [dB]
            "initial_max_dynamic_range": 80,  # [dB]
            "tgc_start": 24,  # [dB]
            "tgc_slope": 5e2,  # [dB/m]
            "tgc_step": 5e-3,  # [m]
            "image_extent_ox": [-19e-3, 19e-3],
            "image_extent_oz": [10e-3, 45e-3],
            "min_tgc": 14, # [dB]
            "max_tgc": 54, # [dB]
        }
        # Compute TGC samples, for a given TGC step.
        tgc_sampling_depths, tgc_curve = compute_tgc_curve_linear(
            oz_min=self._settings["image_extent_oz"][0],
            oz_max=self._settings["image_extent_oz"][1],
            tgc_start=self._settings["tgc_start"],
            tgc_slope=self._settings["tgc_slope"],
            tgc_sampling_step=self._settings["tgc_step"]
        )
        self._settings["tgc_sampling_depths"] = tgc_sampling_depths
        self._settings["tgc_curve"] = tgc_curve

    @property
    def settings(self):
        return self._settings

    def get_bmode(self):
        return self._bmode_data_source.get()

    def get_rf(self):
        return self._rf_data_source.get()

    def set_tgc_curve(self, tgc_curve: np.ndarray):
        print(f"Setting TGC: {tgc_curve}")

    def set_dr_min(self, dr_min: float):
        print(f"Setting DR min: {dr_min}")

    def set_dr_max(self, dr_max: float):
        print(f"Setting DR max: {dr_max}")

    def set_tx_voltage(self, voltage: float):
        print(f"Setting TX voltage: {voltage}")

    def close(self):
        print("Closing model")

