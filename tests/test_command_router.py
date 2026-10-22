from unittest.mock import Mock

import pytest

from nlp_robot_commander.command_router import CommandRouter
from nlp_robot_commander.types import CommandDecision


def test_routes_each_authorized_intent_once():
    actions = Mock()
    router = CommandRouter(actions)

    assert router.route(CommandDecision(True, "navigate", 0.9, destination="cuisine"))
    assert router.route(CommandDecision(True, "stop", 1.0))
    assert router.route(CommandDecision(True, "report", 0.9))

    actions.navigate.assert_called_once_with("cuisine")
    actions.stop.assert_called_once_with()
    actions.report.assert_called_once_with()


def test_rejected_decision_never_reaches_robot():
    actions = Mock()
    assert not CommandRouter(actions).route(CommandDecision(False, "navigate", 0.2))
    assert not actions.method_calls


def test_navigation_without_destination_cannot_be_routed():
    with pytest.raises(ValueError):
        CommandRouter(Mock()).route(CommandDecision(True, "navigate", 0.9))
