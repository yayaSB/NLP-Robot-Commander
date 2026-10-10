#!/usr/bin/env python3
"""Démo locale du pipeline, sans installation de ROS 2."""

import argparse
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path)
    parser.add_argument("--waypoints", type=Path, default=Path("src/nlp_robot_commander/config/waypoints.yaml"))
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
    print("Mode DistilBERT" if args.model else "Mode lexical de secours")
    print("Saisissez `quit` pour quitter.")
    while True:
        try:
            text = input("> ").strip()
        except EOFError:
            break
        if text.casefold() in {"quit", "exit", "q"}:
            break
        print(json.dumps(asdict(processor.process(text)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
