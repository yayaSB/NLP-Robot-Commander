from pathlib import Path

from nlp_robot_commander.command_processor import CommandProcessor
from nlp_robot_commander.entity_extractor import EntityExtractor
from nlp_robot_commander.intent_classifier import RuleBasedIntentClassifier


WAYPOINTS = Path(__file__).parents[1] / "src" / "nlp_robot_commander" / "config" / "waypoints.yaml"


def processor(threshold=0.65):
    return CommandProcessor(
        RuleBasedIntentClassifier(),
        EntityExtractor.from_yaml(WAYPOINTS),
        threshold,
    )


def test_navigation_command_is_accepted_with_destination():
    result = processor().process("Rends-toi dans la cuisine")
    assert result.accepted
    assert result.intent == "navigate"
    assert result.destination == "cuisine"


def test_unknown_navigation_destination_is_rejected():
    result = processor().process("Va dans la chambre")
    assert not result.accepted
    assert result.error_code == "MISSING_DESTINATION"


def test_stop_command_is_accepted():
    result = processor().process("Arrête-toi immédiatement")
    assert result.accepted
    assert result.intent == "stop"


def test_pick_command_extracts_object():
    result = processor().process("Prends la boîte rouge")
    assert result.accepted
    assert result.intent == "pick"
    assert result.object_name == "boite rouge"


def test_report_command_is_accepted():
    result = processor().process("Où te trouves-tu actuellement ?")
    assert result.accepted
    assert result.intent == "report"


def test_empty_and_low_confidence_commands_are_rejected():
    assert processor().process(" ").error_code == "EMPTY_COMMAND"
    assert processor().process("bonjour robot").error_code == "LOW_CONFIDENCE"

