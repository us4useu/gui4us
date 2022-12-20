from dataclasses import dataclass, field


class Event:
    pass


@dataclass(frozen=True)
class MethodCallEvent(Event):
    name: str
    args: tuple = field(default_factory=list)
    kwargs: dict = field(default_factory=dict)


@dataclass(frozen=True)
class CloseEvent:
    pass
