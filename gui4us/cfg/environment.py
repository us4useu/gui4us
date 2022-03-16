from dataclasses import dataclass
import numpy as np
from typing import Union, Iterable


@dataclass(frozen=True)
class LiveDataId:
    name: str
    ordinal: int


@dataclass(frozen=True)
class HardwareEnvironment:
    """
    :param session_cfg: path to the session configuration file
    :param scheme: arrus Scheme describing the processing graph
    :param capture_buffer_capacity: capacity of the capture buffer
    :param log_file: path to the output log file, if None, a default path
        will be used
    :param log_file_level: log file severity level
    """
    session_cfg: str
    scheme: object
    capture_buffer_capacity: int
    log_file: str = None
    log_file_level: str = "INFO"
    initial_tx_voltage: int = 5
    n_tgc_curve_points: int = 1
    initial_tgc_curve: Union[float, Iterable] = 54


@dataclass(frozen=True)
class DatasetEnvironment:
    filepath: str
    processing: object