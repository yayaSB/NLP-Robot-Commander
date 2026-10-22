#!/usr/bin/env python3
"""Contrôle les labels, doublons et fuites entre les trois jeux de données."""

import argparse
import csv
import json
import re
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from pathlib import Path


LABELS = {"navigate", "stop", "report"}


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    without_accents = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )
    return re.sub(r"\W+", " ", without_accents).strip()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--training", type=Path, default=Path("dataset/dataset.csv"))
    parser.add_argument("--test", type=Path, default=Path("dataset/test_commands.csv"))
    parser.add_argument("--max-similarity", type=float, default=0.94)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    training = read_rows(args.training)
    test = read_rows(args.test)
    errors: list[str] = []
    training_labels = {row.get("intent", "") for row in training}
    test_labels = {row.get("expected_intent", "") for row in test}
    if training_labels != LABELS:
        errors.append(f"Labels d'entraînement invalides: {sorted(training_labels)}")
    if test_labels != LABELS:
        errors.append(f"Labels de test invalides: {sorted(test_labels)}")

    records: list[tuple[str, str, str]] = []
    for row in training:
        records.append((row["split"], normalize(row["text"]), row["text"]))
    for row in test:
        records.append(("test", normalize(row["text"]), row["text"]))

    exact: list[dict[str, str]] = []
    for index, left in enumerate(records):
        for right in records[index + 1 :]:
            if left[1] == right[1]:
                exact.append(
                    {"left_split": left[0], "right_split": right[0], "text": left[2]}
                )
    if exact:
        errors.append(f"{len(exact)} doublon(s) exact(s) après normalisation")

    near: list[dict[str, object]] = []
    for index, left in enumerate(records):
        for right in records[index + 1 :]:
            if left[0] == right[0]:
                continue
            ratio = SequenceMatcher(None, left[1], right[1]).ratio()
            if ratio >= args.max_similarity:
                near.append(
                    {
                        "left_split": left[0],
                        "right_split": right[0],
                        "left_text": left[2],
                        "right_text": right[2],
                        "similarity": round(ratio, 4),
                    }
                )
    if near:
        errors.append(f"{len(near)} quasi-doublon(s) inter-splits")

    result = {
        "ok": not errors,
        "labels": sorted(LABELS),
        "training_rows": len(training),
        "test_rows": len(test),
        "training_counts": dict(Counter(row["intent"] for row in training)),
        "split_counts": dict(Counter(row["split"] for row in training)),
        "test_counts": dict(Counter(row["expected_intent"] for row in test)),
        "similarity_threshold": args.max_similarity,
        "exact_duplicates": exact,
        "near_duplicates": near,
        "errors": errors,
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered)
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
