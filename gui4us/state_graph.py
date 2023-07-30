from dataclasses import dataclass
from typing import Union, Set, get_args, Callable, Any
from collections import Iterable
from enum import Enum
import threading

StateId = Union[str, Enum]
ActionId = Union[str, Enum]


class Event:
    def __init__(self, input_state, transition=None):
        self.input_state = input_state
        self.transition = transition
        self.is_continue = True

    def stop(self):
        self.is_continue = False

    def get_result(self):
        return EventResult(is_continue=self.is_continue)


@dataclass(frozen=True)
class EventResult:
    is_continue: bool


@dataclass(frozen=True)
class State:
    id: StateId
    on_enter: Callable[[Event], Any] = None
    on_exit: Callable[[Event], Any] = None


@dataclass(frozen=True)
class Action:
    id: ActionId


@dataclass(frozen=True)
class Transition:
    in_id: StateId
    action: ActionId
    out_id: StateId
    on_enter: callable = None


@dataclass(frozen=True)
class StateGraph:
    states: Set[State]
    actions: Set[Action]
    transitions: Set[Transition]

    def __post_init__(self):
        state_idx = dict((state.id, state) for state in self.states)
        transition_idx = dict(((t.in_id, t.out_id), t)
                              for t in self.transitions)
        action_idx = dict(((t.in_id, t.action), t) for t in self.transitions)
        object.__setattr__(self, "state_idx", state_idx)
        object.__setattr__(self, "transition_idx", transition_idx)
        object.__setattr__(self, "action_idx", action_idx)

    def get_state(self, state: Union[State, StateId]):
        if isinstance(state, State):
            if not state in self.states:
                raise ValueError(f"{state} does not belong to this graph")
            else:
                return state
        try:
            return self.state_idx[state]
        except KeyError:
            raise KeyError(f"There is not state with id {state}")

    def get_transition(self, in_state: Union[State, StateId],
                       out_state: Union[State, StateId]):
        if isinstance(in_state, get_args(StateId)):
            in_id = in_state
        else:
            in_id = in_state.id
        if isinstance(out_state, get_args(StateId)):
            out_id = out_state
        else:
            out_id = out_state.id
        try:
            return self.transition_idx[(in_id, out_id)]
        except KeyError:
            raise KeyError(f"There is no transition from state {in_id} "
                           f"to {out_id}")

    def get_action(self, state: Union[State, StateId],
                   action: Union[Action, ActionId]):
        if isinstance(state, State):
            state = state.id
        if isinstance(action, Action):
            action = action.id
        try:
            return self.action_idx[(state, action)]
        except KeyError:
            raise KeyError(f"The action '{action}' is not available in state "
                           f"'{state}")


class StateGraphIterator:

    def __init__(self, state_graph: StateGraph, start_state: StateId):
        self.state_graph = state_graph
        self.current_state = None
        self.lock = threading.RLock()
        self.enter(start_state)

    def is_current_state(self, state):
        """
        Returns true if the current state is the given state.
        """
        id = self.current_state
        if isinstance(self.current_state, State):
            id = self.current_state.id
        if isinstance(state, Iterable):
            return id in state
        else:
            return id == state

    def assert_state(self, expected_state):
        if self.current_state.id != expected_state:
            raise ValueError(f"Expected state: {expected_state}, "
                             f"actual: {self.current_state}")

    def enter(self, state: Union[State, StateId]):
        """
        Enter given state. Discard the current state (i.e. the on_exit callback
        of the current state will not be called).

        This method is thread-safe.

        :param state: state to enter
        :return: the result of on_enter callback (if defined, otherwise None)
        """
        with self.lock:
            event = Event(state)
            if isinstance(state, State):
                state = state.id
            new_state = self.state_graph.get_state(state)
            in_result = None
            if new_state.on_enter is not None:
                in_result = new_state.on_enter(event)
                if not event.is_continue:
                    return in_result
            self.current_state = state
            return in_result

    def do(self, action: Union[ActionId, Action]):
        """
        Perform action: exit current state, enter transition, then enter new
        state.

        :param action: action to perform
        :return: a tuple: in, transition, out, continue; the first three values
          are the return values of input state on_exit callback,
          transition on_enter callback, output state on_enter callback; the last
          value is True if the transition to the destination state was performed
          False otherwise.
        """
        if isinstance(action, Action):
            action = action.id
        transition = self.state_graph.get_action(self.current_state, action)
        input_state = self.state_graph.get_state(transition.in_id)
        output_state = self.state_graph.get_state(transition.out_id)

        in_result, transition_result, out_result = None, None, None

        with self.lock:
            event = Event(input_state=input_state, transition=transition)
            if input_state.on_exit is not None:
                in_result = input_state.on_exit(event)
                if not event.is_continue:
                    return in_result, transition_result, out_result, False
            if transition.on_enter is not None:
                transition_result = transition.on_enter(event)
                if not event.is_continue:
                    return in_result, transition_result, out_result, False
            if output_state.on_enter is not None:
                out_result = output_state.on_enter(event)
                if not event.is_continue:
                    return in_result, transition_result, out_result, False
            self.current_state = output_state
            return in_result, transition_result, out_result, True

    def go(self, state: Union[State, StateId]):
        transition = self.state_graph.get_transition(self.current_state, state)
        input_state = self.state_graph.get_state(state)
        output_state = self.state_graph.get_state(transition.out_id)

        in_result, transition_result, out_result = None, None, None

        with self.lock:
            event = Event(input_state=input_state, transition=transition)
            if input_state.on_exit is not None:
                in_result = input_state.on_exit(event)
                if not event.is_continue:
                    return in_result, transition_result, out_result, False
            if transition.on_enter is not None:
                transition_result = transition.on_enter(event)
                if not event.is_continue:
                    return in_result, transition_result, out_result, False
            if output_state.on_enter is not None:
                out_result = output_state.on_enter(event)
                if not event.is_continue:
                    return in_result, transition_result, out_result, False
            self.current_state = output_state
            return in_result, transition_result, out_result, True
