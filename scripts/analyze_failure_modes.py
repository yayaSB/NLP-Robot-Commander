#!/usr/bin/env python3
"""Transforme predictions.csv en catalogue synthétique des modes d'échec."""

import argparse
from pathlib import Path

import pandas as pd


DESCRIPTIONS = {
    "WRONG_INTENT": "Mauvaise intention prédite par le classifieur.",
    "WRONG_OR_MISSING_PARAMETER": "Intention correcte mais entité absente ou erronée.",
    "NAVIGATION_FAILURE": "Commande correcte mais objectif refusé ou inaccessible par Nav2.",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--predictions",
        type=Path,
        default=Path("artifacts/test_campaign_3intents/predictions.csv"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/test_campaign_3intents/failure_catalogue.md"),
    )
    args = parser.parse_args()
    frame = pd.read_csv(args.predictions).fillna("")
    failures = frame[frame["failure_mode"] != "NONE"]
    lines = [
        "# Catalogue des modes d'échec mesurés",
        "",
        f"Nombre de commandes analysées : **{len(frame)}**  ",
        f"Nombre d'échecs : **{len(failures)}**",
        "",
    ]
    for mode, description in DESCRIPTIONS.items():
        subset = failures[failures["failure_mode"] == mode]
        lines.extend([f"## {mode} ({len(subset)})", "", description, ""])
        if subset.empty:
            lines.extend(["Aucun cas observé.", ""])
            continue
        lines.extend(["| ID | Commande | Attendu | Prédit | Entité prédite | Notes |", "|---|---|---|---|---|---|"])
        for _, row in subset.iterrows():
            safe_text = str(row["text"]).replace("|", "\\|")
            notes = str(row.get("notes", "")).replace("|", "\\|")
            lines.append(
                f"| {row.get('id', '')} | {safe_text} | {row['expected_intent']} | "
                f"{row['predicted_intent']} | {row.get('predicted_entity', '')} | {notes} |"
            )
        lines.append("")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(f"Catalogue écrit dans {args.output}")


if __name__ == "__main__":
    main()

