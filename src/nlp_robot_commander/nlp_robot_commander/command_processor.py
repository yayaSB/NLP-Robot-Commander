import re
import unicodedata

from .command_memory import CommandMemory
from .entity_extractor import EntityExtractor
from .intent_classifier import IntentClassifier
from .llm_interpreter import LlmError, LlmInterpreter
from .text_utils import normalize_text
from .types import CommandDecision, IntentPrediction, VALID_INTENTS


class CommandProcessor:
    """Transforme une phrase en décision validée, indépendante de ROS 2."""

    def __init__(
        self,
        classifier: IntentClassifier,
        extractor: EntityExtractor,
        confidence_threshold: float = 0.65,
        ambiguity_margin: float = 0.10,
        max_command_chars: int = 240,
        llm_interpreter: LlmInterpreter | None = None,
        memory: CommandMemory | None = None,
        llm_history_size: int = 8,
        allow_llm_fallback: bool = True,
    ) -> None:
        if not 0.0 <= confidence_threshold <= 1.0:
            raise ValueError("confidence_threshold doit être compris entre 0 et 1.")
        if not 0.0 <= ambiguity_margin <= 1.0:
            raise ValueError("ambiguity_margin doit être compris entre 0 et 1.")
        if max_command_chars < 16:
            raise ValueError("max_command_chars doit être supérieur ou égal à 16.")
        if llm_history_size < 1:
            raise ValueError("llm_history_size doit être strictement positif.")
        self.classifier = classifier
        self.extractor = extractor
        self.confidence_threshold = confidence_threshold
        self.ambiguity_margin = ambiguity_margin
        self.max_command_chars = max_command_chars
        self.llm_interpreter = llm_interpreter
        self.memory = memory
        self.llm_history_size = int(llm_history_size)
        self.allow_llm_fallback = bool(allow_llm_fallback)

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
    _DIRECT_REPORT_PATTERNS = (
        r"\bt ou\b",
        r"\bt'(?:es|est) ou\b",
        r"\btu (?:es|est) ou\b",
        r"\btu te trouves ou\b",
    )
    _REPORT_PATTERNS = _DIRECT_REPORT_PATTERNS + (
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
    _MEMORY_REFERENCE_PATTERNS = (
        r"\brefais\b",
        r"\brepete\b",
        r"\bmeme commande\b",
        r"\bcomme (?:avant|la derniere fois)\b",
        r"\bderniere commande\b",
        r"\bcommande precedente\b",
        r"\bretourne la-bas\b",
        r"\breviens la-bas\b",
        r"\bencore une fois\b",
    )

    def is_priority_stop(self, text: str) -> bool:
        """Détecte un arrêt explicite sans effectuer d'appel au LLM."""

        if not isinstance(text, str):
            return False
        normalized = normalize_text(text)
        return not self._matches_any(
            normalized, self._NEGATED_STOP
        ) and self._matches_any(
            normalized,
            self._STOP_PATTERNS,
        )

    def remember(self, text: str, decision: CommandDecision) -> None:
        """Mémorise explicitement une décision après son routage par l'appelant."""

        if self.memory is not None:
            self.memory.record(text, decision)

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
        if self.is_priority_stop(text):
            return CommandDecision(
                True,
                "stop",
                1.0,
                message="Arrêt explicite accepté avec priorité de sécurité.",
                source="safety_rules",
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
        has_sequence_marker = bool(
            re.search(r"\b(?:puis|ensuite|apres cela)\b", normalized)
        )
        has_memory_reference = self._matches_any(
            normalized, self._MEMORY_REFERENCE_PATTERNS
        )
        has_direct_report = self._matches_any(
            normalized, self._DIRECT_REPORT_PATTERNS
        )
        if (has_navigation_marker or has_memory_reference) and has_sequence_marker:
            return CommandDecision(
                False,
                "navigate",
                1.0,
                error_code="SEQUENTIAL_COMMAND",
                message="Les commandes séquentielles ne sont pas autorisées.",
            )

        if has_memory_reference:
            history = self.memory.recent(self.llm_history_size) if self.memory else []
            if not history:
                return CommandDecision(
                    False,
                    "unknown",
                    0.0,
                    error_code="MEMORY_EMPTY",
                    message="Aucune ancienne commande acceptée n'est disponible.",
                    source="memory_rules",
                    memory_used=True,
                )
            if re.search(r"\b(?:retourne|reviens) la-bas\b", normalized):
                record = next(
                    (item for item in reversed(history) if item.intent == "navigate"),
                    None,
                )
            else:
                record = history[-1]
            if record is None or record.intent == "stop":
                return CommandDecision(
                    False,
                    "unknown",
                    0.0,
                    error_code="MEMORY_COMMAND_NOT_REPLAYABLE",
                    message="La commande mémorisée ne peut pas être rejouée.",
                    source="memory_rules",
                    memory_used=True,
                )
            return CommandDecision(
                True,
                record.intent,
                1.0,
                destination=record.destination,
                message="Commande précédente retrouvée dans la mémoire locale.",
                source="memory_rules",
                memory_used=True,
            )

        if has_navigation_marker and len(destinations) == 1:
            return CommandDecision(
                True,
                "navigate",
                1.0,
                destination=destinations[0],
                message="Navigation explicite acceptée par les règles déterministes.",
                source="deterministic_rules",
            )

        if has_direct_report:
            return CommandDecision(
                True,
                "report",
                1.0,
                message=(
                    "Demande de position explicite acceptée par les règles "
                    "déterministes."
                ),
                source="deterministic_rules",
            )

        source = "classifier"
        memory_used = False
        llm_destination = None
        history = []
        if self.llm_interpreter is not None:
            history = (
                self.memory.recent(self.llm_history_size)
                if self.memory is not None
                else []
            )
            try:
                interpretation = self.llm_interpreter.interpret(text, history)
            except LlmError as exc:
                if not self.allow_llm_fallback:
                    return CommandDecision(
                        False,
                        "unknown",
                        0.0,
                        error_code="LLM_UNAVAILABLE",
                        message=str(exc),
                        source="llm",
                    )
                prediction = self.classifier.predict(text)
                source = "classifier_fallback"
            else:
                prediction = IntentPrediction(
                    interpretation.intent,
                    interpretation.confidence,
                )
                source = "llm"
                memory_used = interpretation.uses_memory
                llm_destination = interpretation.destination
        else:
            prediction = self.classifier.predict(text)

        if prediction.intent not in VALID_INTENTS:
            return CommandDecision(
                False,
                prediction.intent,
                prediction.confidence,
                error_code="UNKNOWN_INTENT",
                message="L'intention prédite n'est pas prise en charge.",
                source=source,
                memory_used=memory_used,
            )
        if prediction.confidence < self.confidence_threshold:
            return CommandDecision(
                False,
                prediction.intent,
                prediction.confidence,
                error_code="LOW_CONFIDENCE",
                message="Confiance insuffisante; commande refusée par sécurité.",
                source=source,
                memory_used=memory_used,
            )
        if prediction.intent == "stop":
            return CommandDecision(
                False,
                "unknown",
                prediction.confidence,
                error_code="UNKNOWN_INTENT",
                message="Aucun indice explicite d'arrêt n'a été détecté.",
                source=source,
                memory_used=memory_used,
            )
        if memory_used and (
            not has_memory_reference
            or not any(
                item.intent == prediction.intent
                and item.destination == llm_destination
                for item in history
            )
        ):
            return CommandDecision(
                False,
                prediction.intent,
                prediction.confidence,
                error_code="LLM_MEMORY_MISMATCH",
                message=(
                    "La décision attribuée à la mémoire ne correspond à aucune "
                    "commande acceptée de l'historique."
                ),
                source=source,
                memory_used=True,
            )
        contextual_decision = memory_used and has_memory_reference
        if prediction.intent == "report" and not (
            self._matches_any(normalized, self._REPORT_PATTERNS)
            or contextual_decision
        ):
            return CommandDecision(
                False,
                "unknown",
                prediction.confidence,
                error_code="UNKNOWN_INTENT",
                message=(
                    "Aucun indice explicite de demande de position n'a été détecté."
                ),
                source=source,
                memory_used=memory_used,
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
                    source=source,
                    memory_used=memory_used,
                )

        entities = self.extractor.extract(text, prediction.intent)
        destination = entities.destination
        if prediction.intent == "navigate" and source == "llm":
            if llm_destination not in {None, *self.extractor.waypoints}:
                return CommandDecision(
                    False,
                    prediction.intent,
                    prediction.confidence,
                    error_code="LLM_DESTINATION_INVALID",
                    message="Le LLM a proposé une destination non autorisée.",
                    source=source,
                    memory_used=memory_used,
                )
            if destination and llm_destination and destination != llm_destination:
                return CommandDecision(
                    False,
                    prediction.intent,
                    prediction.confidence,
                    error_code="LLM_DESTINATION_CONFLICT",
                    message=(
                        "La destination du texte contredit celle proposée par le LLM."
                    ),
                    source=source,
                    memory_used=memory_used,
                )
            destination = destination or llm_destination
            if not entities.destination and destination and not (
                has_navigation_marker or contextual_decision
            ):
                return CommandDecision(
                    False,
                    prediction.intent,
                    prediction.confidence,
                    error_code="UNSUPPORTED_CONTEXT_INFERENCE",
                    message="La destination inférée manque d'indice de navigation sûr.",
                    source=source,
                    memory_used=memory_used,
                )
        if prediction.intent == "navigate" and not destination:
            return CommandDecision(
                False,
                prediction.intent,
                prediction.confidence,
                error_code="UNKNOWN_DESTINATION",
                message="La destination n'est pas un waypoint connu.",
                source=source,
                memory_used=memory_used,
            )

        return CommandDecision(
            True,
            prediction.intent,
            prediction.confidence,
            destination=destination,
            message=(
                "Commande acceptée via le classifieur de secours; le LLM local "
                "était indisponible."
                if source == "classifier_fallback"
                else "Commande acceptée."
            ),
            source=source,
            memory_used=memory_used,
        )

    @staticmethod
    def _matches_any(text: str, patterns: tuple[str, ...]) -> bool:
        return any(re.search(pattern, text) for pattern in patterns)
