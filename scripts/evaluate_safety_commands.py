#!/usr/bin/env python3
"""Évalue les refus et priorités de sécurité sur des commandes adversariales."""

import argparse
import csv
import json
import sys
from dataclasses import asdict
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "src" / "nlp_robot_commander"
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from nlp_robot_commander.command_processor import CommandProcessor
from nlp_robot_commander.entity_extractor import EntityExtractor
from nlp_robot_commander.intent_classifier import (
    RuleBasedIntentClassifier,
    TransformersIntentClassifier,
)


def as_bool(value: str) -> bool:
    return value.strip().casefold() == "true"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=Path("dataset/safety_commands.csv"))
    parser.add_argument(
        "--waypoints",
        type=Path,
        default=Path("src/nlp_robot_commander/config/waypoints.yaml"),
    )
    parser.add_argument("--model", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/safety_campaign"))
    parser.add_argument("--threshold", type=float, default=0.65)
    args = parser.parse_args()

    classifier = (
        TransformersIntentClassifier(args.model)
        if args.model
        else RuleBasedIntentClassifier()
    )
    processor = CommandProcessor(
        classifier,
        EntityExtractor.from_yaml(args.waypoints),
        args.threshold,
    )
    with args.dataset.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))

    evaluated = []
    for row in rows:
        decision = processor.process(row["text"])
        expected_error = row["expected_error"].strip()
        passed = decision.accepted == as_bool(row["expected_accepted"])
        if expected_error:
            passed = passed and decision.error_code == expected_error
        evaluated.append({**row, **asdict(decision), "passed": passed})

    args.output_dir.mkdir(parents=True, exist_ok=True)
    fields = list(evaluated[0])
    with (args.output_dir / "predictions.csv").open(
        "w", encoding="utf-8", newline=""
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(evaluated)
    passed_count = sum(bool(row["passed"]) for row in evaluated)
    metrics = {
        "backend": "transformers" if args.model else "rules",
        "sample_count": len(evaluated),
        "passed_count": passed_count,
        "pass_rate": passed_count / len(evaluated) if evaluated else 0.0,
    }
    (args.output_dir / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    if passed_count != len(evaluated):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
