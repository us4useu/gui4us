"""The view descriptor must be strict JSON: e.g. an ARRUS pipeline parameter with an unbounded Box(-inf, inf)
used to produce `Infinity`, which the browser's JSON.parse rejects (the whole view stayed empty)."""
import json
import unittest

import numpy as np

from gui4us.model import Box, SettingDef
from gui4us.view.session import ViewSession, _to_jsonable


class DescriptorJsonTest(unittest.TestCase):

    def test_unbounded_setting_is_strict_json(self):
        setting = SettingDef(name="power_dr_min",
                             space=Box(low=-np.inf, high=np.inf, shape=(1,), dtype=np.float32),
                             initial_value=np.float32(50.0))
        descriptor = ViewSession._setting_descriptor(setting)
        text = json.dumps(descriptor, allow_nan=False)  # raises ValueError on Infinity/NaN
        decoded = json.loads(text)
        self.assertIsNone(decoded["low"])
        self.assertIsNone(decoded["high"])
        self.assertEqual(decoded["initial_value"], 50.0)

    def test_to_jsonable_nested(self):
        value = {"a": [1.0, np.inf, np.float32(np.nan)], "b": np.array([-np.inf, 2.0]), "c": (np.int64(3),)}
        self.assertEqual(_to_jsonable(value), {"a": [1.0, None, None], "b": [None, 2.0], "c": [3]})


if __name__ == "__main__":
    unittest.main()
