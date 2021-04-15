from model import Model
import dataclasses
import numpy as np
import threading
import queue
import logging

_LOGGER = logging.getLogger("Controller")


class Event:
    pass


@dataclasses.dataclass(frozen=True)
class SetTgcCurveEvent(Event):
    tgc_curve: np.ndarray


@dataclasses.dataclass(frozen=True)
class SetDrMinEvent(Event):
    dr_min: float


@dataclasses.dataclass(frozen=True)
class SetDrMaxEvent(Event):
    dr_max: float


@dataclasses.dataclass(frozen=True)
class SetVoltageEvent(Event):
    voltage: float


@dataclasses.dataclass(frozen=True)
class CloseEvent(Event):
    pass


class Controller:
    def __init__(self, model: Model):
        self.model = model
        self._event_queue = queue.Queue()
        self._result_queue = queue.Queue()
        self._event_queue_runner = threading.Thread(target=self._controller_thread)
        self._event_queue_runner.start()
        self._actions = {
            SetTgcCurveEvent: self.model.set_tgc_curve,
            SetVoltageEvent: self.model.set_tx_voltage,
            SetDrMinEvent: self.model.set_dr_min,
            SetDrMaxEvent: self.model.set_dr_max
        }

    @property
    def settings(self):
        return self.model.settings

    def get_bmode(self):
        return self.model.get_bmode()

    def get_rf(self):
        return self.model.get_rf()

    def send(self, event: Event):
        self._event_queue.put(event)

    def close(self):
        self._event_queue.put(CloseEvent())

    def start(self):
        # TODO event
        self.model.start()

    def _controller_thread(self):
        while True:
            try:
                event = self._event_queue.get()
                if isinstance(event, CloseEvent):
                    return
                logging.info(f"Got event type: {type(event)}")
                self._actions[type(event)](**dataclasses.asdict(event))
            except Exception as e:
                logging.exception(e)


