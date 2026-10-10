from dataclasses import dataclass, field
from typing import Mapping, Optional


VALID_INTENTS = ("navigate", "stop", "pick", "report")


@dataclass(frozen=True)
class IntentPrediction:
    intent: str
    confidence: float
    scores: Mapping[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class EntityExtraction:
    destination: Optional[str] = None
    object_name: Optional[str] = None


@dataclass(frozen=True)
class CommandDecision:
    accepted: bool
    intent: str
    confidence: float
    destination: Optional[str] = None
    object_name: Optional[str] = None
    error_code: Optional[str] = None
    message: str = ""

