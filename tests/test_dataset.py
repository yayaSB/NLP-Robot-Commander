import csv
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_training_dataset_is_balanced_and_has_80_rows():
    with (ROOT / "dataset" / "dataset.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 80
    assert Counter(row["intent"] for row in rows) == {
        "navigate": 20,
        "stop": 20,
        "pick": 20,
        "report": 20,
    }
    assert all(row["text"].strip() for row in rows)


def test_campaign_has_50_unique_rows():
    with (ROOT / "dataset" / "test_commands.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 50
    assert len({row["id"] for row in rows}) == 50
    assert set(row["expected_intent"] for row in rows) == {
        "navigate",
        "stop",
        "pick",
        "report",
    }

