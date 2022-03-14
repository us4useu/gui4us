from gui4us.model.model import Model
import dataclasses
import threading
import queue
import logging

_LOGGER = logging.getLogger("Controller")


class Event:
    pass


@dataclasses.dataclass(frozen=True)
class SetGainEvent(Event):
    gain_value: float


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
            SetGainEvent: self.model.set_gain_value,
            SetVoltageEvent: self.model.set_tx_voltage,
        }

    @property
    def settings(self):
        return self.model.settings

    def get_rf_sum(self):
        return self.model.get_rf_sum()

    def get_defect_mask(self):
        return self.model.get_defect_mask()

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


