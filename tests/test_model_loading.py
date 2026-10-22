import pytest

from nlp_robot_commander.intent_classifier import ModelLoadError, TransformersIntentClassifier


def test_missing_checkpoint_has_explicit_error():
    with pytest.raises(ModelLoadError):
        TransformersIntentClassifier("models/checkpoint-that-does-not-exist")
