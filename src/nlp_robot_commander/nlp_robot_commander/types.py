from dataclasses import dataclass, field
from typing import Mapping, Optional


VALID_INTENTS = ("navigate", "stop", "report")


@dataclass(frozen=True)
class IntentPrediction:
    intent: str
    confidence: float
    scores: Mapping[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class EntityExtraction:
    destination: Optional[str] = None


@dataclass(frozen=True)
class CommandDecision:
    accepted: bool
    intent: str
    confidence: float
    destination: Optional[str] = None
    error_code: Optional[str] = None
    message: str = ""
    source: str = "classifier"
    memory_used: bool = False


@dataclass(frozen=True)
class LlmInterpretation:
    """Sortie structurée et non exécutable produite par le LLM."""

    intent: str
    confidence: float
    destination: Optional[str] = None
    uses_memory: bool = False
    explanation: str = ""

