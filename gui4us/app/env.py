from typing import Dict
from flask import Flask, redirect
import threading
import multiprocessing as mp
from enum import Enum, auto
from dataclasses import dataclass, field

import gui4us.state_graph
from gui4us.state_graph import (
    StateGraph, StateGraphIterator, State, Action, Transition
)
from gui4us.controller.env import EnvController
from gui4us.view import View

# TODO jak naprawic multiprocessing + logging?

_DEFAULT_TIMEOUT = 60  # [s]


class StateId(Enum):
    CREATED = auto()
    RUNNING = auto()
    CLOSED = auto()


class ActionId(Enum):
    RUN = auto()
    CLOSE = auto()
    GET_VIEW_PORT = auto()
    GET_VIEW_SCRIPT = auto()


@dataclass(frozen=True)
class Event:
    id: Enum
    kwargs: dict = field(default_factory=dict)


class EnvironmentApplication:
    """
    An interface to the environment process.

    This class is intended to be used only by gui4us internals
    (for jupyter notebook interface create a custom View).

    :param cfg_path: path to the environment configuration package; if None,
        null (dummy) environment will be created
    """
    def __init__(self, id: int, cfg_path: str = None):
        self.id = id
        self.cfg_path = cfg_path
        self._action_lock = threading.Lock()
        self._event_queue = mp.Queue()
        self._event_result_queue = mp.Queue()
        self.process = mp.Process(
            target=_controller_main,
            kwargs=dict(
                id=self.id,
                cfg_path=self.cfg_path,
                event_queue=self._event_queue,
                event_result_queue=self._event_result_queue
            )
        )
        self.process.daemon = True
        self._state_graph = StateGraph(
            states={
                State(id=StateId.CREATED),
                State(id=StateId.RUNNING),
                State(id=StateId.CLOSED),
            },
            actions={
                Action(ActionId.RUN),
                Action(ActionId.CLOSE)
            },
            transitions={
                Transition(
                    in_id=StateId.CREATED,
                    out_id=StateId.RUNNING,
                    action=ActionId.RUN,
                    on_enter=self._run_impl
                ),
                Transition(
                    in_id=StateId.RUNNING,
                    out_id=StateId.CLOSED,
                    action=ActionId.CLOSE,
                    on_enter=self._close_impl
                ),
                Transition(
                    in_id=StateId.CREATED,
                    out_id=StateId.CLOSED,
                    action=ActionId.CLOSE,
                    on_enter=None,  # Nothing is running: just change the state
                ),
                Transition(
                    in_id=StateId.CLOSED,
                    out_id=StateId.CLOSED,
                    action=ActionId.CLOSE,
                    on_enter=None,  # Nothing is running: just keep the state
                )
            }
        )
        self._state = StateGraphIterator(
            state_graph=self._state_graph,
            start_state=StateId.CREATED
        )

    def run(self):
        return self._state.do(ActionId.RUN)

    def _run_impl(self):
        # NOTE: this is state transition callback, therefore you can assume
        # with self._state.lock context
        self.process.start()
        result = self._event_result_queue.get(timeout=_DEFAULT_TIMEOUT)
        return self._handle_result(result)

    def close(self):
        return self._state.do(ActionId.CLOSE)

    def _close_impl(self):
        # NOTE: this is state transition callback, therefore you can assume
        # with self._state.lock context
        result = self._do(ActionId.CLOSE)
        self.process.join(timeout=_DEFAULT_TIMEOUT)
        return result

    def get_view_port(self) -> int:
        with self._state.lock:
            self._state.assert_state(StateId.RUNNING)
            return self._do(ActionId.GET_VIEW_PORT)

    def get_view_script(self) -> str:
        with self._state.lock:
            self._state.assert_state(StateId.RUNNING)
            return self._do(ActionId.GET_VIEW_SCRIPT)

    def _do(self, event: Enum, **kwargs):
        with self._state.lock, self._action_lock:
            self._state.assert_state(StateId.RUNNING)
            self._event_queue.put(event)
            result = self._event_result_queue.get(timeout=_DEFAULT_TIMEOUT)
            print(f"Got result {result} for event: {event}")
            return self._handle_result(result)

    def _handle_result(self, result):
        if isinstance(result, Exception):
            raise result
        else:
            return result


class EnvironmentApplicationController:
    """
    An implementation of an environment controller.
    """

    def __init__(
            self, id: int, cfg_path: str,
            event_queue: mp.Queue,
            event_result_queue: mp.Queue
    ):
        self.id = id
        self.cfg_path = cfg_path
        self.env: EnvController = EnvController(
            id=f"env_{id}",
            env_cfg_path=self.cfg_path
        )
        self.view: View = View(cfg_path=self.cfg_path)
        # TODO connect view with environment
        self.event_queue = event_queue
        self.event_result_queue = event_result_queue
        self._thread = threading.Thread(target=self._run_controller_loop)
        self._thread_is_ready = threading.Event()

    def run(self):
        self._thread.start()
        self._thread_is_ready.wait(timeout=_DEFAULT_TIMEOUT)
        self.view.run()

    def close(self):
        self.view.close()
        self.env.close()

    def join(self):
        self._thread.join()

    def get_view_port(self) -> int:
        return self.view.port

    def get_view_script(self) -> str:
        return self.view.script

    def _run_controller_loop(self):
        action_map = {
            ActionId.GET_VIEW_PORT: self.get_view_port,
            ActionId.GET_VIEW_SCRIPT: self.get_view_script
        }
        print("Us4R controller started.")
        self._thread_is_ready.set()
        while True:
            event: Event = self.event_queue.get()
            print(f"Event: {event}")
            if event.id == ActionId.CLOSE:
                self.close()
                break
            else:
                action = action_map[event.id]
                try:
                    result = action(**event.kwargs)
                    print(f"Event: {event.id}, result: {result}")
                    try:
                        self.event_result_queue.put(result)
                    except Exception as e:
                        print(f"Error while sending result for action: "
                                     "{event}, result: {result}")
                        print(e)
                except Exception as e:
                    print(e)
                    self.event_result_queue.put(e)
        # Exit model context.
        print("Model closed")
        self.event_result_queue.put(None)
        print("Exiting")
        return


def _controller_main(
        id: int,
        cfg_path: str,
        event_queue: mp.Queue,
        event_result_queue: mp.Queue
):
    try:
        controller = EnvironmentApplicationController(
            id=id,
            cfg_path=cfg_path,
            event_queue=event_queue,
            event_result_queue=event_result_queue
        )
        controller.run()
        # Close the process gracefully.
        controller.join()
    except Exception as e:
        print(e)

