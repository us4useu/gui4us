from abc import abstractmethod, ABC
from typing import Callable, Dict
from dataclasses import dataclass, field
from typing import Optional, Sequence, Union, Tuple, Any
from numbers import Number
from enum import Enum

import numpy as np
from numpy import dtype

EnvId = str
StreamId = str


@dataclass(frozen=True)
class StreamDataId:
    """
    ID of a particular stream metadata array.
    """
    name: StreamId
    ordinal: int


class Stream(ABC):
    """
    Represents a stream of data produced synchronously.
    """

    @abstractmethod
    def append_on_new_data_callback(
            self,
            callback: Callable[[Tuple[np.ndarray, ...]], Any]
    ):
        """
        A signal emitted when new data (observations) arrive.
        """
        raise NotImplementedError()


class Metadata(ABC):
    pass


class MetadataCollection:
    """
    Metadata describing a collection (map) of output data.
    """

    def __init__(self, metadata_coll: Dict[StreamDataId, Metadata]):
        self.metadata_coll = metadata_coll

    def output(self, key: StreamDataId):
        return self.metadata_coll[key]


class Unit:
    dB = "dB"
    pixel = "pixel"
    V = "V"  # Voltage


@dataclass
class Space:
    shape: Sequence[int] = field(default=None, init=False)
    dtype: object = field(default=np.float32, init=False)
    name: Optional[Sequence[str]] = field(default=None, init=False)
    unit: Optional[Sequence[Union[Unit, str]]] = field(default=None, init=False)

    def __init__(self, shape, dtype, name=None, unit=None):
        self.shape = shape
        self.dtype = dtype
        self.name = name
        self.unit = unit

    def is_empty(self):
        return len(self.shape) == 0

    def is_scalar(self):
        return len(self.shape) == 1 and self.shape[0] == 1

    def is_vector(self):
        return len(self.shape) == 1 and self.shape[0] > 1


class ContinuousRange(ABC):
    pass


@dataclass
class Box(Space):
    low: np.ndarray
    high: np.ndarray

    def __init__(self, low, high, shape, dtype, name=None, unit=None):
        super().__init__(shape, dtype, name, unit)
        self.low = low
        self.high = high


@dataclass
class ActionDef:
    name: str
    space: Space

    def create_action(self, value):
        return Action(name=self.name, value=value)


@dataclass(frozen=True)
class Action:
    name: str
    value: np.ndarray


@dataclass(frozen=True)
class SetAction:
    name: str
    value: np.ndarray


@dataclass
class SettingDef:
    name: str
    space: Space
    initial_value: Union[np.ndarray, Number]
    step: Number = 1

    def create_set_action(self, value):
        return SetAction(
            name=self.name,
            value=value
        )


class Env(ABC):

    @abstractmethod
    def start(self) -> None:
        raise NotImplementedError()

    @abstractmethod
    def stop(self) -> None:
        raise NotImplementedError()

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError()

    @abstractmethod
    def set(self, set_action: SetAction):
        pass

    @abstractmethod
    def get_settings(self) -> Sequence[SettingDef]:
        return []

    @abstractmethod
    def get_stream(self) -> Stream:
        raise NotImplementedError()

    @abstractmethod
    def get_stream_metadata(self) -> MetadataCollection:
        raise NotImplementedError()
