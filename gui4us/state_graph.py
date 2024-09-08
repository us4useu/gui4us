from dataclasses import dataclass
from typing import Union, Set, Iterable

StateId = str
ActionId = str


@dataclass(frozen=True)
class State:
    id: StateId
    on_enter: callable = None
    on_exit: callable = None


@dataclass(frozen=True)
class Action:
    id: ActionId


@dataclass(frozen=True)
class Transition:
    in_id: StateId
    action: ActionId
    out_id: StateId
    on_enter: callable = None


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
            return state
        try:
            return self.state_idx[state]
        except KeyError:
            raise KeyError(f"There is not state with id {state}")

    def get_transition(self, in_state: Union[State, StateId],
                       out_state: Union[State, StateId]):

        in_id = in_state if isinstance(in_state, StateId) else in_state.id
        out_id = out_state if isinstance(out_state, StateId) else out_state.id
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
        # index states by id
        self.enter(start_state)

    def is_current_state(self, state):
        id = self.current_state
        if isinstance(self.current_state, State):
            id = self.current_state.id
        if isinstance(state, Iterable):
            return id in state
        else:
            return id == state

    def enter(self, state: Union[State, StateId]):
        event = Event(state)
        if isinstance(state, State):
            state = state.id
        new_state = self.state_graph.get_state(state)
        if new_state.on_enter is not None:
            new_state.on_enter(event)
            if not event.is_continue:
                return
        self.current_state = state

    def do(self, action: Union[ActionId, Action]):
        if isinstance(action, Action):
            action = action.id
        transition = self.state_graph.get_action(self.current_state, action)
        input_state = self.state_graph.get_state(transition.in_id)
        output_state = self.state_graph.get_state(transition.out_id)

        event = Event(input_state=input_state, transition=transition)
        if input_state.on_exit is not None:
            input_state.on_exit(event)
            if not event.is_continue:
                return event.get_result()
        if transition.on_enter is not None:
            transition.on_enter(event)
            if not event.is_continue:
                return event.get_result()
        if output_state.on_enter is not None:
            output_state.on_enter(event)
            if not event.is_continue:
                return event.get_result()
        self.current_state = output_state
        return event.get_result()

    def go(self, state: Union[State, StateId]):
        transition = self.state_graph.get_transition(self.current_state, state)
        input_state = self.state_graph.get_state(state)
        output_state = self.state_graph.get_state(transition.out_id)

        event = Event(input_state=input_state, transition=transition)
        if input_state.on_exit is not None:
            input_state.on_exit(event)
            if not event.is_continue:
                return
        if transition.on_enter is not None:
            transition.on_enter(event)
            if not event.is_continue:
                return
        if output_state.on_enter is not None:
            output_state.on_enter(event)
            if not event.is_continue:
                return
        self.current_state = output_state
