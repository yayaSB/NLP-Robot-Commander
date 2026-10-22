from pathlib import Path

import pytest

from nlp_robot_commander.entity_extractor import EntityExtractor


WAYPOINTS = (
    Path(__file__).parents[1]
    / "src"
    / "nlp_robot_commander"
    / "config"
    / "waypoints.yaml"
)


def extractor():
    return EntityExtractor.from_yaml(WAYPOINTS)


def test_extracts_canonical_destination_from_alias():
    assert extractor().extract_destination("Rejoins le dock de recharge") == "chargeur"
    assert extractor().extract_destination("Va à la salle de travail") == "bureau"


def test_destination_matching_ignores_case_accents_and_punctuation():
    assert extractor().extract_destination("VA DANS LA CUISINE !") == "cuisine"
    assert extractor().extract_destination("Rejoins le sejour.") == "salon"


def test_unknown_and_multiple_destinations_are_not_single_targets():
    assert extractor().extract_destination("Va dans la chambre") is None
    assert extractor().extract_destination("Cuisine ou salon") is None
    assert extractor().extract_destinations("Cuisine ou salon") == ["cuisine", "salon"]


def test_waypoint_coordinates_are_numeric():
    waypoint = extractor().waypoint("cuisine")
    assert waypoint["x"] == pytest.approx(1.25)
    assert waypoint["yaw"] == pytest.approx(1.57)


def test_ambiguous_alias_is_rejected():
    with pytest.raises(ValueError, match="Alias ambigu"):
        EntityExtractor(
            {
                "a": {"x": 0, "y": 0, "aliases": ["commun"]},
                "b": {"x": 1, "y": 1, "aliases": ["commun"]},
            }
        )
