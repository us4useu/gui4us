from dataclasses import dataclass
import numpy as np
from typing import Union, Iterable





@dataclass(frozen=True)
class LinearFunction:
    intercept: float
    slope: float


@dataclass(frozen=True)
class UltrasoundEnvironment:
    """
    Note: initial TGC curve value is

    :param session_cfg: path to the session configuration file
    :param tx_rx_sequence: TX/RX sequence. Note: the tgc curve value
      (tgc_start, tgc_slope, tgc_curve) will be ignored in favor of
      the tgc_curve parameter
    :param processing: processing implementation
    :param work_mode: HOST, ASYNC or MANUAL
    :param capture_buffer_capacity: capacity of the capture buffer
    :param log_file: path to the output log file, if None, a default path
        will be used
    :param log_file_level: log file severity level
    :param tgc_curve: initial tgc curve to apply
    :param tgc_sampling: the distance between TGC curve sampling points
    """
    session_cfg: str
    tx_rx_sequence: object
    pipeline: object
    work_mode: str
    # Logging
    log_file: str = None
    log_file_level: str = "INFO"
    # Buffers
    rx_buffer_size: int = 4
    host_buffer_size: int = 4
    capture_buffer_capacity: int = 100
    # Voltage
    tx_voltage: int = 5
    tx_voltage_step: int = 1
    # TGC
    tgc_curve: float = 54
    tgc_step: float = 1
    tgc_sampling: float = 5e-3


@dataclass(frozen=True)
class DatasetEnvironment:
    filepath: str
    processing: object
