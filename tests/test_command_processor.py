from pathlib import Path

import pytest

from nlp_robot_commander.command_processor import CommandProcessor
from nlp_robot_commander.command_memory import CommandMemory
from nlp_robot_commander.entity_extractor import EntityExtractor
from nlp_robot_commander.intent_classifier import RuleBasedIntentClassifier
from nlp_robot_commander.llm_interpreter import LlmUnavailableError
from nlp_robot_commander.types import IntentPrediction, LlmInterpretation


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


def processor(
    classifier=None,
    threshold=0.65,
    max_chars=240,
    llm=None,
    memory=None,
    allow_llm_fallback=True,
):
    return CommandProcessor(
        classifier or RuleBasedIntentClassifier(),
        EntityExtractor.from_yaml(WAYPOINTS),
        threshold,
        max_command_chars=max_chars,
        llm_interpreter=llm,
        memory=memory,
        allow_llm_fallback=allow_llm_fallback,
    )


class FakeLlm:
    def __init__(self, interpretation=None, error=None) -> None:
        self.interpretation = interpretation
        self.error = error
        self.history = None

    def interpret(self, _text, history):
        self.history = history
        if self.error:
            raise self.error
        return self.interpretation


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


def test_llm_can_resolve_explicit_reference_to_previous_command(tmp_path):
    memory = CommandMemory(tmp_path / "memory.sqlite3")
    seed = processor(memory=memory)
    previous = seed.process("Va dans la cuisine")
    seed.remember("Va dans la cuisine", previous)
    llm = FakeLlm(LlmInterpretation("navigate", 0.94, "cuisine", True))

    result = processor(llm=llm, memory=memory).process(
        "Refais la dernière commande"
    )

    assert result.accepted
    assert result.destination == "cuisine"
    assert result.source == "llm"
    assert result.memory_used
    assert llm.history[-1].destination == "cuisine"
    memory.close()


def test_llm_destination_cannot_override_explicit_destination():
    llm = FakeLlm(LlmInterpretation("navigate", 0.95, "cuisine", False))

    result = processor(llm=llm).process("Va dans le salon")

    assert not result.accepted
    assert result.error_code == "LLM_DESTINATION_CONFLICT"


def test_llm_cannot_claim_memory_that_does_not_exist():
    llm = FakeLlm(LlmInterpretation("navigate", 0.95, "cuisine", True))

    result = processor(llm=llm).process("Refais la dernière commande")

    assert not result.accepted
    assert result.error_code == "LLM_MEMORY_MISMATCH"


def test_llm_memory_destination_must_match_history(tmp_path):
    memory = CommandMemory(tmp_path / "memory.sqlite3")
    seed = processor(memory=memory)
    previous = seed.process("Va dans le salon")
    seed.remember("Va dans le salon", previous)
    llm = FakeLlm(LlmInterpretation("navigate", 0.95, "cuisine", True))

    result = processor(llm=llm, memory=memory).process(
        "Refais la dernière commande"
    )

    assert not result.accepted
    assert result.error_code == "LLM_MEMORY_MISMATCH"
    memory.close()


def test_llm_cannot_invent_an_implicit_stop():
    llm = FakeLlm(LlmInterpretation("stop", 0.99, None, False))

    result = processor(llm=llm).process("Fais ce qu'il faut")

    assert not result.accepted
    assert result.error_code == "UNKNOWN_INTENT"


def test_llm_unavailability_uses_explicitly_configured_fallback():
    llm = FakeLlm(error=LlmUnavailableError("serveur arrêté"))

    result = processor(llm=llm).process("Où te trouves-tu ?")

    assert result.accepted
    assert result.intent == "report"
    assert result.source == "classifier_fallback"


def test_llm_unavailability_can_fail_closed():
    llm = FakeLlm(error=LlmUnavailableError("serveur arrêté"))

    result = processor(llm=llm, allow_llm_fallback=False).process(
        "Où te trouves-tu ?"
    )

    assert not result.accepted
    assert result.error_code == "LLM_UNAVAILABLE"
