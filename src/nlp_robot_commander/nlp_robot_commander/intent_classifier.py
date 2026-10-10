from pathlib import Path
from typing import Protocol

from .text_utils import normalize_text
from .types import IntentPrediction, VALID_INTENTS


class IntentClassifier(Protocol):
    def predict(self, text: str) -> IntentPrediction: ...


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
        "pick": (
            "prends",
            "prendre",
            "ramasse",
            "saisis",
            "attrape",
            "recupere",
            "recupere",
            "souleve",
            "va chercher",
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
        # La politique pour une commande multi-intention privilégie le premier indice.
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
            raise RuntimeError(
                "Installez torch et transformers pour utiliser le checkpoint DistilBERT."
            ) from exc

        model_path = str(model_path)
        self._torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_path, fix_mistral_regex=False
        )
        self.model = AutoModelForSequenceClassification.from_pretrained(model_path)
        self.model.eval()
        self.max_length = max_length

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
        id2label = {int(key): value for key, value in self.model.config.id2label.items()}
        scores = {id2label[index]: float(score) for index, score in enumerate(probabilities)}
        intent = max(scores, key=scores.get)
        return IntentPrediction(intent, scores[intent], scores)
