import re
import math
from pathlib import Path
from typing import Any, Mapping

import yaml

from .text_utils import normalize_text
from .types import EntityExtraction


class EntityExtractor:
    """Valide les waypoints et extrait les destinations autorisées."""

    def __init__(self, waypoints: Mapping[str, Mapping[str, Any]]) -> None:
        if not isinstance(waypoints, Mapping) or not waypoints:
            raise ValueError("La configuration doit contenir au moins un waypoint.")
        self.waypoints: dict[str, Mapping[str, Any]] = {}
        self._destination_aliases: list[tuple[str, str]] = []
        alias_owners: dict[str, str] = {}
        for canonical, data in waypoints.items():
            if not isinstance(canonical, str) or not canonical.strip():
                raise ValueError("Chaque waypoint doit avoir un nom non vide.")
            if not isinstance(data, Mapping):
                raise ValueError(f"Waypoint invalide: {canonical}")
            coordinates: dict[str, float] = {}
            for key in ("x", "y", "yaw"):
                try:
                    value = float(data.get(key, 0.0 if key == "yaw" else None))
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"Coordonnée {key} invalide pour {canonical}.") from exc
                if not math.isfinite(value):
                    raise ValueError(f"Coordonnée {key} non finie pour {canonical}.")
                coordinates[key] = value
            aliases = data.get("aliases", [])
            if not isinstance(aliases, list) or not all(
                isinstance(alias, str) and alias.strip() for alias in aliases
            ):
                raise ValueError(f"Alias invalides pour {canonical}.")
            self.waypoints[canonical] = {**data, **coordinates}
            aliases = [canonical, *data.get("aliases", [])]
            for alias in aliases:
                normalized = normalize_text(alias)
                owner = alias_owners.get(normalized)
                if owner and owner != canonical:
                    raise ValueError(
                        f"Alias ambigu '{alias}' partagé par {owner} et {canonical}."
                    )
                alias_owners[normalized] = canonical
                self._destination_aliases.append((normalized, canonical))
        self._destination_aliases.sort(key=lambda item: len(item[0]), reverse=True)

    @classmethod
    def from_yaml(cls, path: str | Path) -> "EntityExtractor":
        with Path(path).open(encoding="utf-8") as stream:
            config = yaml.safe_load(stream) or {}
        waypoints = config.get("waypoints")
        if not isinstance(waypoints, dict) or not waypoints:
            raise ValueError(f"Aucun waypoint valide dans {path}")
        unknown_keys = set(config) - {"waypoints"}
        if unknown_keys:
            raise ValueError(f"Clés de configuration inconnues: {sorted(unknown_keys)}")
        return cls(waypoints)

    def extract(self, text: str, intent: str) -> EntityExtraction:
        if intent == "navigate":
            return EntityExtraction(destination=self.extract_destination(text))
        return EntityExtraction()

    def extract_destination(self, text: str) -> str | None:
        destinations = self.extract_destinations(text)
        return destinations[0] if len(destinations) == 1 else None

    def extract_destinations(self, text: str) -> list[str]:
        normalized = normalize_text(text)
        found: list[tuple[int, str]] = []
        for alias, canonical in self._destination_aliases:
            match = re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", normalized)
            if match and canonical not in {item[1] for item in found}:
                found.append((match.start(), canonical))
        return [canonical for _, canonical in sorted(found)]

    def waypoint(self, destination: str) -> Mapping[str, Any]:
        try:
            return self.waypoints[destination]
        except KeyError as exc:
            raise KeyError(f"Waypoint inconnu: {destination}") from exc
