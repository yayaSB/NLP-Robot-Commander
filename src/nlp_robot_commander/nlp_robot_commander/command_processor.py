from .entity_extractor import EntityExtractor
from .intent_classifier import IntentClassifier
from .types import CommandDecision, VALID_INTENTS


class CommandProcessor:
    """Transforme une phrase en décision validée, indépendante de ROS 2."""

    def __init__(
        self,
        classifier: IntentClassifier,
        extractor: EntityExtractor,
        confidence_threshold: float = 0.65,
    ) -> None:
        self.classifier = classifier
        self.extractor = extractor
        self.confidence_threshold = confidence_threshold

    def process(self, text: str) -> CommandDecision:
        if not text or not text.strip():
            return CommandDecision(
                False,
                "unknown",
                0.0,
                error_code="EMPTY_COMMAND",
                message="La commande est vide.",
            )

        prediction = self.classifier.predict(text)
        if prediction.intent not in VALID_INTENTS:
            return CommandDecision(
                False,
                prediction.intent,
                prediction.confidence,
                error_code="UNKNOWN_INTENT",
                message="L'intention prédite n'est pas prise en charge.",
            )
        if prediction.confidence < self.confidence_threshold:
            return CommandDecision(
                False,
                prediction.intent,
                prediction.confidence,
                error_code="LOW_CONFIDENCE",
                message="Confiance insuffisante; commande refusée par sécurité.",
            )

        entities = self.extractor.extract(text, prediction.intent)
        if prediction.intent == "navigate" and not entities.destination:
            return CommandDecision(
                False,
                prediction.intent,
                prediction.confidence,
                error_code="MISSING_DESTINATION",
                message="La destination n'est pas un waypoint connu.",
            )
        if prediction.intent == "pick" and not entities.object_name:
            return CommandDecision(
                False,
                prediction.intent,
                prediction.confidence,
                error_code="MISSING_OBJECT",
                message="Aucun objet n'a été extrait.",
            )

        return CommandDecision(
            True,
            prediction.intent,
            prediction.confidence,
            destination=entities.destination,
            object_name=entities.object_name,
            message="Commande acceptée.",
        )
