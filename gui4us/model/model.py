from gui4us.common import *


class Environment:

    def get_n_outputs(self):
        raise ValueError("NYI")

    def get_output(self, name: str) -> DataBuffer:
        raise ValueError("NYI")

    def get_output_metadata(self, ordinal) -> ImageMetadata:
        raise ValueError("NYI")

    def start(self):
        raise ValueError("NYI")

    def stop(self):
        raise ValueError("NYI")

    def close(self):
        raise ValueError("NYI")

    def set(self, key: str, value: object):
        raise ValueError("NYI")
