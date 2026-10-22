import re
import unicodedata

from .entity_extractor import EntityExtractor
from .intent_classifier import IntentClassifier
from .text_utils import normalize_text
from .types import CommandDecision, VALID_INTENTS


class CommandProcessor:
    """Transforme une phrase en décision validée, indépendante de ROS 2."""

    def __init__(
        self,
        classifier: IntentClassifier,
        extractor: EntityExtractor,
        confidence_threshold: float = 0.65,
        ambiguity_margin: float = 0.10,
        max_command_chars: int = 240,
    ) -> None:
        if not 0.0 <= confidence_threshold <= 1.0:
            raise ValueError("confidence_threshold doit être compris entre 0 et 1.")
        if not 0.0 <= ambiguity_margin <= 1.0:
            raise ValueError("ambiguity_margin doit être compris entre 0 et 1.")
        if max_command_chars < 16:
            raise ValueError("max_command_chars doit être supérieur ou égal à 16.")
        self.classifier = classifier
        self.extractor = extractor
        self.confidence_threshold = confidence_threshold
        self.ambiguity_margin = ambiguity_margin
        self.max_command_chars = max_command_chars

    _STOP_PATTERNS = (
        r"\barrete(?:-toi|z-vous)?\b",
        r"\bstop\b",
        r"\bstoppe(?:r|z)?\b",
        r"\bhalte\b",
        r"\bimmobilise(?:-toi|z-vous)?\b",
        r"\bannule(?:r|z)?\b",
        r"\bannulation\b",
        r"\binterromps\b",
        r"\bcesse\b",
        r"\bne bouge plus\b",
        r"\bn'avance plus\b",
        r"\bne plus avancer\b",
        r"\bne continue plus\b",
        r"\bfreine\b",
        r"\bgarde (?:ta|cette) position\b",
        r"\breste (?:exactement )?(?:ici|sur place)\b",
        r"\babandonne\b",
        r"\bsuspends?\b",
        r"\bcoupe\b",
        r"\barret\b",
        r"\binterruption\b",
        r"\bimmobilisation\b",
        r"\bmettre fin\b",
        r"\bt'arret(?:e|er)\b",
    )
    _NEGATED_STOP = (
        r"\bne\s+(?:t'|vous\s+)?arrete\s+pas\b",
        r"\bn'arrete\s+pas\b",
        r"\bne\s+stoppe\s+pas\b",
    )
    _NEGATED_NAVIGATION = (
        r"\bne\s+va\s+pas\b",
        r"\bn'y\s+va\s+pas\b",
        r"\bne\s+te\s+rends\s+pas\b",
        r"\bne\s+navigue\s+pas\b",
        r"\bne\s+te\s+deplace\s+pas\b",
    )
    _OUT_OF_SCOPE_ACTIONS = (
        r"\bprends?\b",
        r"\bramass(?:e|er)\b",
        r"\bsaisis?\b",
        r"\battrap(?:e|er)\b",
        r"\brecuper(?:e|er)\b",
        r"\bsoulev(?:e|er)\b",
        r"\bva chercher\b",
    )
    _NAVIGATION_MARKERS = (
        "va ",
        "rends-toi",
        "rejoins",
        "navigue",
        "dirige-toi",
        "deplace-toi",
        "retourne",
    )
    _REPORT_PATTERNS = (
        r"\bou (?:es-tu|se situe|te trouves-tu)\b",
        r"\bou en es-tu\b",
        r"\bou (?:tu )?te situes\b",
        r"\bposition\b",
        r"\bcoordonnees?\b",
        r"\bx y\b",
        r"\blocalisation\b",
        r"\blocalise\b",
        r"\bemplacement\b",
        r"\bendroit\b",
        r"\bpose\b",
        r"\brepere map\b",
        r"\bbase_link\b",
        r"\bindique tf\b",
        r"\brapporte\b",
    )

    def process(self, text: str) -> CommandDecision:
        if not isinstance(text, str) or not text.strip():
            return CommandDecision(
                False,
                "unknown",
                0.0,
                error_code="EMPTY_COMMAND",
                message="La commande est vide.",
            )
        if len(text) > self.max_command_chars:
            return CommandDecision(
                False,
                "unknown",
                0.0,
                error_code="COMMAND_TOO_LONG",
                message=f"La commande dépasse {self.max_command_chars} caractères.",
            )
        if any(unicodedata.category(char) == "Cc" for char in text):
            return CommandDecision(
                False,
                "unknown",
                0.0,
                error_code="CONTROL_CHARACTER",
                message="La commande contient un caractère de contrôle.",
            )

        normalized = normalize_text(text)
        if self._matches_any(normalized, self._NEGATED_STOP):
            return CommandDecision(
                False,
                "stop",
                1.0,
                error_code="NEGATED_STOP",
                message="Une demande d'arrêt négative est ambiguë et a été refusée.",
            )
        if self._matches_any(normalized, self._STOP_PATTERNS):
            return CommandDecision(
                True,
                "stop",
                1.0,
                message="Arrêt explicite accepté avec priorité de sécurité.",
            )
        if self._matches_any(normalized, self._OUT_OF_SCOPE_ACTIONS):
            return CommandDecision(
                False,
                "unknown",
                0.0,
                error_code="UNSUPPORTED_ACTION",
                message="Cette action ne fait pas partie des capacités autorisées.",
            )
        if self._matches_any(normalized, self._NEGATED_NAVIGATION):
            return CommandDecision(
                False,
                "navigate",
                1.0,
                error_code="NEGATED_COMMAND",
                message="La navigation niée a été refusée.",
            )

        destinations = self.extractor.extract_destinations(text)
        if len(destinations) > 1:
            return CommandDecision(
                False,
                "navigate",
                1.0,
                error_code="MULTIPLE_DESTINATIONS",
                message="Plusieurs destinations ont été détectées; commande refusée.",
            )
        has_navigation_marker = any(
            marker in normalized for marker in self._NAVIGATION_MARKERS
        )
        if has_navigation_marker and re.search(r"\b(?:puis|ensuite|apres cela)\b", normalized):
            return CommandDecision(
                False,
                "navigate",
                1.0,
                error_code="SEQUENTIAL_COMMAND",
                message="Les commandes séquentielles ne sont pas autorisées.",
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
        if prediction.intent == "stop":
            return CommandDecision(
                False,
                "unknown",
                prediction.confidence,
                error_code="UNKNOWN_INTENT",
                message="Aucun indice explicite d'arrêt n'a été détecté.",
            )
        if prediction.intent == "report" and not self._matches_any(
            normalized, self._REPORT_PATTERNS
        ):
            return CommandDecision(
                False,
                "unknown",
                prediction.confidence,
                error_code="UNKNOWN_INTENT",
                message="Aucun indice explicite de demande de position n'a été détecté.",
            )

        ordered_scores = sorted(prediction.scores.values(), reverse=True)
        if len(ordered_scores) >= 2:
            score_gap = ordered_scores[0] - ordered_scores[1]
            if score_gap < self.ambiguity_margin:
                return CommandDecision(
                    False,
                    prediction.intent,
                    prediction.confidence,
                    error_code="AMBIGUOUS_INTENT",
                    message="Les deux intentions les plus probables sont trop proches.",
                )

        entities = self.extractor.extract(text, prediction.intent)
        if prediction.intent == "navigate" and not entities.destination:
            return CommandDecision(
                False,
                prediction.intent,
                prediction.confidence,
                error_code="UNKNOWN_DESTINATION",
                message="La destination n'est pas un waypoint connu.",
            )

        return CommandDecision(
            True,
            prediction.intent,
            prediction.confidence,
            destination=entities.destination,
            message="Commande acceptée.",
        )

    @staticmethod
    def _matches_any(text: str, patterns: tuple[str, ...]) -> bool:
        return any(re.search(pattern, text) for pattern in patterns)
