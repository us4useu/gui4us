from dataclasses import dataclass
import typing


@dataclass(frozen=True)
class ContinuousRange:
    """
    A continuous range [start, end].
    """
    start: float
    end: float
    default_step: float = 1


@dataclass(frozen=True)
class List:
    values: typing.List


@dataclass(frozen=True)
class Set:
    values: typing.Set


# Data types
@dataclass(frozen=True)
class Setting:
    """
    :param domain: domain of each value in this setting (i.e. each value of
       tensor with given shape)
    param label: a tuple of strings, each string is a parameter label
    """
    id: str
    data_type: str
    domain: typing.Union[ContinuousRange, List, Set]
    init_value: typing.Any
    unit: str
    shape: tuple = (1, )
    label: tuple = None   # Tuple of strings

    def is_scalar(self):
        return len(self.shape) == 1 and self.shape[0] == 1

    def is_vector(self):
        return len(self.shape) == 1 and self.shape[0] > 1


@dataclass(frozen=True)
class SettingPresentation:
    type: str
    params: dict
