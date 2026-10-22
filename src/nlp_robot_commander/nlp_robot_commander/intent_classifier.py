from pathlib import Path
from typing import Protocol

from .text_utils import normalize_text
from .types import IntentPrediction, VALID_INTENTS


class IntentClassifier(Protocol):
    def predict(self, text: str) -> IntentPrediction: ...


class ModelLoadError(RuntimeError):
    """Erreur explicite de chargement ou de compatibilité du checkpoint."""


class RuleBasedIntentClassifier:
    """Secours déterministe pour la démo; DistilBERT reste le classifieur principal."""

    KEYWORDS = {
        "stop": (
            "arrete",
            "stop",
            "halte",
            "immobilise",
            "immobilisation",
            "annule",
            "interromps",
            "abandonne",
            "freine",
            "ne bouge plus",
            "n'avance",
            "cesse",
            "garde ta position",
        ),
        "report": (
            "ou es-tu",
            "ou te trouves-tu",
            "ou tu es",
            "ou tu te trouves",
            "position",
            "localisation",
            "localise-toi",
            "coordonnees",
            "emplacement",
            "dans quelle piece",
            "x et ton y",
        ),
        "navigate": (
            "va dans",
            "va au",
            "aller",
            "rends-toi",
            "rejoins",
            "navigue",
            "dirige-toi",
            "deplace-toi",
            "retourne",
            "direction",
            "au bureau",
            "retour base",
            "mets-toi en route",
        ),
    }

    def predict(self, text: str) -> IntentPrediction:
        normalized = normalize_text(text)
        raw_scores = {
            intent: sum(1 for keyword in keywords if keyword in normalized)
            for intent, keywords in self.KEYWORDS.items()
        }
        if not any(raw_scores.values()):
            return IntentPrediction(
                "unknown", 0.0, {intent: 0.0 for intent in VALID_INTENTS}
            )

        positions = {
            intent: min(
                (normalized.find(keyword) for keyword in keywords if keyword in normalized),
                default=len(normalized) + 1,
            )
            for intent, keywords in self.KEYWORDS.items()
        }
        best = sorted(VALID_INTENTS, key=lambda name: (-raw_scores[name], positions[name]))[0]
        top_score = raw_scores[best]
        confidence = 0.90 if top_score >= 2 else 0.78 if top_score == 1 else 0.25
        total = sum(raw_scores.values()) or 1
        scores = {intent: score / total for intent, score in raw_scores.items()}
        return IntentPrediction(best, confidence, scores)


class TransformersIntentClassifier:
    """Charge un checkpoint Hugging Face enregistré par le script d'entraînement."""

    def __init__(self, model_path: str | Path, max_length: int = 128) -> None:
        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except ImportError as exc:
            raise ModelLoadError(
                "Installez torch et transformers pour utiliser le checkpoint DistilBERT."
            ) from exc

        path = Path(model_path).expanduser()
        if not path.is_dir():
            raise ModelLoadError(f"Checkpoint introuvable ou non lisible: {path}")

        self._torch = torch
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(
                str(path), local_files_only=True, fix_mistral_regex=False
            )
            self.model = AutoModelForSequenceClassification.from_pretrained(
                str(path), local_files_only=True
            )
        except Exception as exc:
            raise ModelLoadError(f"Checkpoint invalide dans {path}: {exc}") from exc

        id2label = {
            int(key): str(value).casefold()
            for key, value in self.model.config.id2label.items()
        }
        if set(id2label.values()) != set(VALID_INTENTS) or len(id2label) != len(
            VALID_INTENTS
        ):
            raise ModelLoadError(
                "Le checkpoint doit exposer exactement les labels "
                f"{list(VALID_INTENTS)}; labels trouvés: {sorted(id2label.values())}."
            )
        self._id2label = id2label
        self.model.eval()
        self.max_length = int(max_length)
        if self.max_length < 8:
            raise ValueError("max_length doit être supérieur ou égal à 8.")

    def predict(self, text: str) -> IntentPrediction:
        encoded = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=self.max_length,
        )
        with self._torch.no_grad():
            logits = self.model(**encoded).logits[0]
            probabilities = self._torch.softmax(logits, dim=-1).cpu().tolist()
        scores = {
            self._id2label[index]: float(score)
            for index, score in enumerate(probabilities)
        }
        intent = max(scores, key=scores.get)
        return IntentPrediction(intent, scores[intent], scores)
