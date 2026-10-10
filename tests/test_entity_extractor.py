from pathlib import Path

from nlp_robot_commander.entity_extractor import EntityExtractor


WAYPOINTS = Path(__file__).parents[1] / "src" / "nlp_robot_commander" / "config" / "waypoints.yaml"


def extractor():
    return EntityExtractor.from_yaml(WAYPOINTS)


def test_extracts_canonical_destination_from_alias():
    assert extractor().extract_destination("Rejoins le dock de recharge") == "chargeur"
    assert extractor().extract_destination("Va à la salle de travail") == "bureau"


def test_destination_matching_ignores_case_accents_and_punctuation():
    assert extractor().extract_destination("VA DANS LA CUISINE !") == "cuisine"
    assert extractor().extract_destination("Rejoins le sejour.") == "salon"


def test_unknown_destination_is_rejected():
    assert extractor().extract_destination("Va dans la chambre") is None


def test_extracts_and_normalizes_object():
    assert extractor().extract_object("Prends la boîte écarlate située devant toi") == "boite rouge"
    assert extractor().extract_object("Ramasse le cube bleu puis attends") == "cube bleu"


def test_object_extraction_handles_politeness_and_long_determiners():
    assert extractor().extract_object("Ramasse, si possible, le petit cube bleu") == "cube bleu"
    assert extractor().extract_object("Saisis cette bouteille puis attends") == "bouteille"
    assert extractor().extract_object("Soulève doucement le cube") == "cube"
    assert extractor().extract_object("Récupère l'objet de couleur verte") == "objet vert"

