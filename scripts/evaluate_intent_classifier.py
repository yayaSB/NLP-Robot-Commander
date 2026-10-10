#!/usr/bin/env python3
"""Évalue un checkpoint sur un CSV et produit métriques, prédictions et matrice."""

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "src" / "nlp_robot_commander"
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from nlp_robot_commander.entity_extractor import EntityExtractor
from nlp_robot_commander.intent_classifier import TransformersIntentClassifier
from nlp_robot_commander.text_utils import normalize_text

LABELS = ["navigate", "stop", "pick", "report"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, default=Path("dataset/test_commands.csv"))
    parser.add_argument("--waypoints", type=Path, default=Path("src/nlp_robot_commander/config/waypoints.yaml"))
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/test_campaign"))
    parser.add_argument("--threshold", type=float, default=0.65)
    return parser.parse_args()


def clean_optional(value) -> str:
    return "" if pd.isna(value) else str(value).strip()


def infer_failure(row: pd.Series) -> str:
    if row["predicted_intent"] != row["expected_intent"]:
        return "WRONG_INTENT"
    expected_entity = normalize_text(clean_optional(row.get("expected_entity", "")))
    predicted_entity = normalize_text(clean_optional(row.get("predicted_entity", "")))
    if expected_entity != predicted_entity and row["expected_intent"] in {"navigate", "pick"}:
        return "WRONG_OR_MISSING_PARAMETER"
    nav_result = clean_optional(row.get("nav_result", "")).casefold()
    if nav_result in {"failed", "aborted", "inaccessible", "echec", "échec"}:
        return "NAVIGATION_FAILURE"
    return "NONE"


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(args.dataset)
    if not {"text", "expected_intent"}.issubset(frame.columns):
        raise ValueError("Le CSV doit contenir text et expected_intent.")

    classifier = TransformersIntentClassifier(args.model)
    extractor = EntityExtractor.from_yaml(args.waypoints)
    predictions = [classifier.predict(text) for text in frame["text"]]
    frame["predicted_intent"] = [prediction.intent for prediction in predictions]
    frame["confidence"] = [round(prediction.confidence, 6) for prediction in predictions]
    frame["predicted_entity"] = [
        extractor.extract(text, prediction.intent).destination
        or extractor.extract(text, prediction.intent).object_name
        or ""
        for text, prediction in zip(frame["text"], predictions)
    ]
    frame["accepted_by_confidence"] = frame["confidence"] >= args.threshold
    frame["command_accepted"] = frame.apply(
        lambda row: bool(
            row["accepted_by_confidence"]
            and not (
                row["predicted_intent"] in {"navigate", "pick"}
                and not clean_optional(row["predicted_entity"])
            )
        ),
        axis=1,
    )
    frame["failure_mode"] = frame.apply(infer_failure, axis=1)
    frame.to_csv(args.output_dir / "predictions.csv", index=False)

    report = classification_report(
        frame["expected_intent"],
        frame["predicted_intent"],
        labels=LABELS,
        target_names=LABELS,
        output_dict=True,
        zero_division=0,
    )
    metrics = {
        "accuracy": float(accuracy_score(frame["expected_intent"], frame["predicted_intent"])),
        "sample_count": len(frame),
        "confidence_threshold": args.threshold,
        "below_threshold_count": int((~frame["accepted_by_confidence"]).sum()),
        "accepted_command_count": int(frame["command_accepted"].sum()),
        "classification_report": report,
        "failure_counts": frame["failure_mode"].value_counts().to_dict(),
    }
    (args.output_dir / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    matrix = confusion_matrix(frame["expected_intent"], frame["predicted_intent"], labels=LABELS)
    plt.figure(figsize=(7, 6))
    sns.heatmap(matrix, annot=True, fmt="d", cmap="Blues", xticklabels=LABELS, yticklabels=LABELS)
    plt.xlabel("Intention prédite")
    plt.ylabel("Intention réelle")
    plt.title("Matrice de confusion — campagne de test")
    plt.tight_layout()
    plt.savefig(args.output_dir / "confusion_matrix.png", dpi=180)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
