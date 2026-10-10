import re
from pathlib import Path
from typing import Any, Mapping

import yaml

from .text_utils import normalize_text
from .types import EntityExtraction


class EntityExtractor:
    """Extrait une destination connue ou un objet sans dépendre d'un modèle NER."""

    PICK_VERBS = (
        "prends",
        "prendre",
        "ramasse",
        "ramasser",
        "saisis",
        "saisir",
        "attrape",
        "attraper",
        "recupere",
        "recuperer",
        "souleve",
        "soulever",
        "va chercher",
    )

    def __init__(
        self,
        waypoints: Mapping[str, Mapping[str, Any]],
        object_aliases: Mapping[str, str] | None = None,
    ) -> None:
        self.waypoints = dict(waypoints)
        self.object_aliases = {
            normalize_text(key): normalize_text(value)
            for key, value in (object_aliases or {}).items()
        }
        self._destination_aliases: list[tuple[str, str]] = []
        for canonical, data in self.waypoints.items():
            aliases = [canonical, *data.get("aliases", [])]
            self._destination_aliases.extend(
                (normalize_text(alias), canonical) for alias in aliases
            )
        self._destination_aliases.sort(key=lambda item: len(item[0]), reverse=True)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "EntityExtractor":
        with Path(path).open(encoding="utf-8") as stream:
            config = yaml.safe_load(stream) or {}
        waypoints = config.get("waypoints")
        if not isinstance(waypoints, dict) or not waypoints:
            raise ValueError(f"Aucun waypoint valide dans {path}")
        return cls(waypoints, config.get("object_aliases", {}))

    def extract(self, text: str, intent: str) -> EntityExtraction:
        if intent == "navigate":
            return EntityExtraction(destination=self.extract_destination(text))
        if intent == "pick":
            return EntityExtraction(object_name=self.extract_object(text))
        return EntityExtraction()

    def extract_destination(self, text: str) -> str | None:
        normalized = normalize_text(text)
        for alias, canonical in self._destination_aliases:
            if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", normalized):
                return canonical
        return None

    def extract_object(self, text: str) -> str | None:
        normalized = normalize_text(text)
        verb_pattern = "|".join(re.escape(verb) for verb in self.PICK_VERBS)
        match = re.search(rf"(?:{verb_pattern})\s+(.+)", normalized)
        if not match:
            # Forme passive fréquente: « le colis doit être récupéré ».
            passive = re.search(r"^(?:le|la|un|une|ce|cette)\s+(.+?)\s+doit\s+etre", normalized)
            return passive.group(1).strip() if passive else None

        candidate = match.group(1).strip()
        candidate = re.sub(r"^(?:si possible|doucement|delicatement)\s+", "", candidate)
        candidate = re.sub(
            r"^(?:cette|les|une|cet|des|le|la|un|ce|l')\s*", "", candidate
        )
        candidate = re.sub(r"^(?:petit|petite)\s+", "", candidate)
        candidate = re.split(
            r"\b(?:puis|ensuite|et ensuite|qui|situee?|posee?|devant|sur le sol|au sol)\b",
            candidate,
            maxsplit=1,
        )[0].strip()
        for source, target in self.object_aliases.items():
            candidate = re.sub(rf"(?<!\w){re.escape(source)}(?!\w)", target, candidate)
        return candidate or None

    def waypoint(self, destination: str) -> Mapping[str, Any]:
        try:
            return self.waypoints[destination]
        except KeyError as exc:
            raise KeyError(f"Waypoint inconnu: {destination}") from exc
