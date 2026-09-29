import types
import unittest

try:
    from gui4us.model.envs.arrus import _n_ops_per_sequence
except ImportError:  # ARRUS not installed
    _n_ops_per_sequence = None


def _metadata(n_ops):
    return types.SimpleNamespace(
        context=types.SimpleNamespace(raw_sequence=types.SimpleNamespace(ops=[None]*n_ops)))


@unittest.skipIf(_n_ops_per_sequence is None, "ARRUS is not installed")
class NOpsPerSequenceTest(unittest.TestCase):

    def test_simple_sequence_with_two_pipeline_outputs(self):
        # One LinSequence (no .ops), a pipeline with an intermediate Output(): two metadata
        # entries, still ONE sequence.
        scheme = types.SimpleNamespace(tx_rx_sequence=types.SimpleNamespace())
        self.assertEqual(_n_ops_per_sequence(scheme, (_metadata(192), _metadata(192))), [192])

    def test_raw_sequences(self):
        scheme = types.SimpleNamespace(tx_rx_sequence=[
            types.SimpleNamespace(ops=[None]*3), types.SimpleNamespace(ops=[None]*5)])
        self.assertEqual(_n_ops_per_sequence(scheme, (_metadata(3), )), [3, 5])


if __name__ == "__main__":
    unittest.main()
