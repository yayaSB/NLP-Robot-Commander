from nlp_robot_commander.text_utils import normalize_text


def test_normalization():
    assert normalize_text("  Où ÉS-tu ? ") == "ou es-tu"
