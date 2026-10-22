from pathlib import Path

import pytest

from nlp_robot_commander.command_processor import CommandProcessor
from nlp_robot_commander.entity_extractor import EntityExtractor
from nlp_robot_commander.intent_classifier import RuleBasedIntentClassifier
from nlp_robot_commander.types import IntentPrediction


WAYPOINTS = (
    Path(__file__).parents[1]
    / "src"
    / "nlp_robot_commander"
    / "config"
    / "waypoints.yaml"
)


class FixedClassifier:
    def __init__(self, intent: str, confidence: float, scores=None) -> None:
        self.prediction = IntentPrediction(intent, confidence, scores or {})

    def predict(self, _text: str) -> IntentPrediction:
        return self.prediction


def processor(classifier=None, threshold=0.65, max_chars=240):
    return CommandProcessor(
        classifier or RuleBasedIntentClassifier(),
        EntityExtractor.from_yaml(WAYPOINTS),
        threshold,
        max_command_chars=max_chars,
    )


def test_navigation_command_is_accepted_with_destination():
    result = processor().process("Rends-toi dans la cuisine")
    assert result.accepted
    assert result.intent == "navigate"
    assert result.destination == "cuisine"


def test_unknown_navigation_destination_is_rejected():
    result = processor().process("Va dans la chambre")
    assert not result.accepted
    assert result.error_code == "UNKNOWN_DESTINATION"


def test_explicit_stop_has_safety_priority():
    result = processor().process("Va dans la cuisine et arrête-toi")
    assert result.accepted
    assert result.intent == "stop"
    assert result.confidence == 1.0

    mixed = processor().process("Prends la boîte puis arrête-toi")
    assert mixed.accepted
    assert mixed.intent == "stop"


def test_report_command_is_accepted():
    result = processor().process("Où te trouves-tu actuellement ?")
    assert result.accepted
    assert result.intent == "report"


@pytest.mark.parametrize(
    ("text", "error"),
    [
        (" ", "EMPTY_COMMAND"),
        ("bonjour robot", "UNKNOWN_INTENT"),
        ("Prends la boîte rouge", "UNSUPPORTED_ACTION"),
        ("Ne va pas dans la cuisine", "NEGATED_COMMAND"),
        ("Ne t'arrête pas", "NEGATED_STOP"),
        ("Va dans la cuisine pas dans le salon", "MULTIPLE_DESTINATIONS"),
        ("Va dans la cuisine puis dans le laboratoire", "SEQUENTIAL_COMMAND"),
        ("commande\x07", "CONTROL_CHARACTER"),
    ],
)
def test_dangerous_or_invalid_commands_are_rejected(text, error):
    result = processor().process(text)
    assert not result.accepted
    assert result.error_code == error


def test_too_long_command_is_rejected():
    result = processor(max_chars=16).process("a" * 17)
    assert result.error_code == "COMMAND_TOO_LONG"


def test_low_confidence_is_rejected():
    result = processor(FixedClassifier("report", 0.4)).process("Donne ta position")
    assert result.error_code == "LOW_CONFIDENCE"


def test_close_model_scores_are_rejected_as_ambiguous():
    classifier = FixedClassifier(
        "report", 0.75, {"navigate": 0.10, "stop": 0.44, "report": 0.46}
    )
    result = processor(classifier).process("Donne ta position")
    assert result.error_code == "AMBIGUOUS_INTENT"


def test_threshold_and_size_configuration_are_validated():
    with pytest.raises(ValueError):
        processor(threshold=1.2)
    with pytest.raises(ValueError):
        processor(max_chars=8)
