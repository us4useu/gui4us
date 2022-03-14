from dataclasses import dataclass


@dataclass(frozen=True)
class LiveDataId:
    name: str
    ordinal: int


@dataclass(frozen=True)
class HardwareDataSource:
    session_cfg: str
    scheme: object