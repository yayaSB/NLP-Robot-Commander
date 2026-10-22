from nlp_robot_commander.navigation_state import (
    NavigationPhase,
    NavigationStateMachine,
    StopState,
)


def test_stop_without_active_goal_is_immediately_confirmed():
    state = NavigationStateMachine()
    outcome = state.request_stop()
    assert outcome.state == StopState.CONFIRMED
    assert outcome.reason == "no_active_goal"


def test_cancel_request_is_not_a_stop_confirmation():
    state = NavigationStateMachine()
    state.request_goal("cuisine")
    assert not state.goal_response(True)
    outcome = state.request_stop()
    assert outcome.state == StopState.PENDING
    assert state.phase == NavigationPhase.CANCEL_PENDING
    response = state.cancellation_response(True)
    assert response.state == StopState.PENDING
    confirmed = state.complete("canceled")
    assert confirmed is not None
    assert confirmed.state == StopState.CONFIRMED


def test_cancel_rejection_or_timeout_is_unconfirmed():
    for callback in (
        lambda state: state.cancellation_response(False),
        lambda state: state.cancellation_timeout(),
    ):
        state = NavigationStateMachine()
        state.request_goal("salon")
        state.goal_response(True)
        state.request_stop()
        assert callback(state).state == StopState.UNCONFIRMED


def test_stop_while_goal_response_pending_cancels_after_acceptance():
    state = NavigationStateMachine()
    state.request_goal("bureau")
    assert state.request_stop().state == StopState.PENDING
    assert state.goal_response(True)
    assert state.phase == NavigationPhase.CANCEL_PENDING
