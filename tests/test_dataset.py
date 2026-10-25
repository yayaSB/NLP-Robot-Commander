import csv
import re
import unicodedata
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).parents[1]
LABELS = {"navigate", "stop", "report"}


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    without_accents = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )
    return re.sub(r"\W+", " ", without_accents).strip()


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_training_dataset_uses_curated_splits_and_balanced_validation():
    rows = read_csv(ROOT / "dataset" / "dataset.csv")
    assert len(rows) == 192
    assert Counter(row["intent"] for row in rows) == {
        "navigate": 74,
        "stop": 60,
        "report": 58,
    }
    assert Counter(row["split"] for row in rows) == {
        "train": 156,
        "validation": 36,
    }
    assert Counter(
        row["intent"] for row in rows if row["split"] == "validation"
    ) == {"navigate": 12, "stop": 12, "report": 12}
    assert {row["intent"] for row in rows} == LABELS
    assert all(row["text"].strip() for row in rows)


def test_train_validation_and_test_have_no_exact_leakage():
    training = read_csv(ROOT / "dataset" / "dataset.csv")
    test = read_csv(ROOT / "dataset" / "test_commands.csv")
    groups = {
        "train": {normalize(row["text"]) for row in training if row["split"] == "train"},
        "validation": {
            normalize(row["text"])
            for row in training
            if row["split"] == "validation"
        },
        "test": {normalize(row["text"]) for row in test},
    }
    assert groups["train"].isdisjoint(groups["validation"])
    assert groups["train"].isdisjoint(groups["test"])
    assert groups["validation"].isdisjoint(groups["test"])


def test_independent_campaign_is_balanced_and_unique():
    rows = read_csv(ROOT / "dataset" / "test_commands.csv")
    assert len(rows) == 45
    assert len({row["id"] for row in rows}) == 45
    assert Counter(row["expected_intent"] for row in rows) == {
        "navigate": 15,
        "stop": 15,
        "report": 15,
    }


def test_safety_campaign_contains_required_cases():
    rows = read_csv(ROOT / "dataset" / "safety_commands.csv")
    assert len(rows) >= 15
    assert {"negation", "sequence", "multiple_destinations", "hors_domaine"}.issubset(
        {row["category"] for row in rows}
    )
