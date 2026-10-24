import json
import socket
from collections.abc import Callable, Sequence
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from .command_memory import CommandRecord
from .types import LlmInterpretation, VALID_INTENTS


class LlmError(RuntimeError):
    """Erreur contrôlée lors de l'interprétation par le LLM."""


class LlmUnavailableError(LlmError):
    """Le serveur local Ollama ou le modèle n'est pas disponible."""


class LlmResponseError(LlmError):
    """Le serveur a répondu, mais la sortie n'est pas sûre ou valide."""


class LlmInterpreter(Protocol):
    def interpret(
        self, text: str, history: Sequence[CommandRecord]
    ) -> LlmInterpretation: ...


class OllamaLlmInterpreter:
    """Interprète une commande via Ollama sans donner accès au robot au LLM."""

    def __init__(
        self,
        allowed_destinations: Sequence[str],
        model: str = "llama3.2:1b",
        endpoint: str = "http://127.0.0.1:11434",
        timeout_sec: float = 20.0,
        opener: Callable[..., Any] = urlopen,
    ) -> None:
        destinations = tuple(sorted(set(allowed_destinations)))
        if not destinations:
            raise ValueError("Au moins une destination autorisée est requise.")
        if not model.strip():
            raise ValueError("Le nom du modèle Ollama est vide.")
        if timeout_sec <= 0:
            raise ValueError("timeout_sec doit être strictement positif.")

        parsed = urlparse(endpoint)
        if parsed.scheme != "http" or parsed.hostname not in {
            "127.0.0.1",
            "localhost",
            "::1",
        }:
            raise ValueError(
                "L'endpoint Ollama doit être local et utiliser HTTP "
                "(127.0.0.1, localhost ou ::1)."
            )
        if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
            raise ValueError("L'endpoint Ollama ne doit pas contenir de chemin.")

        self.allowed_destinations = destinations
        self.model = model.strip()
        self.endpoint = endpoint.rstrip("/")
        self.timeout_sec = float(timeout_sec)
        self._opener = opener

    def interpret(
        self, text: str, history: Sequence[CommandRecord]
    ) -> LlmInterpretation:
        schema = self._response_schema()
        payload = {
            "model": self.model,
            "stream": False,
            "format": schema,
            "options": {"temperature": 0},
            "messages": [
                {"role": "system", "content": self._system_prompt(schema)},
                {"role": "user", "content": self._user_prompt(text, history)},
            ],
        }
        request = Request(
            f"{self.endpoint}/api/chat",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self._opener(request, timeout=self.timeout_sec) as response:
                envelope = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:300]
            raise LlmUnavailableError(
                f"Ollama a refusé la requête (HTTP {exc.code}): {detail}"
            ) from exc
        except (URLError, TimeoutError, socket.timeout) as exc:
            raise LlmUnavailableError(
                f"Ollama local est indisponible à {self.endpoint}: {exc}"
            ) from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise LlmResponseError("Réponse HTTP Ollama non JSON.") from exc

        try:
            content = envelope["message"]["content"]
            parsed = json.loads(content)
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            raise LlmResponseError(
                "Sortie structurée Ollama absente ou invalide."
            ) from exc
        return self._validate_response(parsed)

    def _validate_response(self, data: Any) -> LlmInterpretation:
        if not isinstance(data, dict):
            raise LlmResponseError("La sortie du LLM doit être un objet JSON.")
        required = {
            "intent",
            "destination",
            "confidence",
            "uses_memory",
            "explanation",
        }
        if set(data) != required:
            raise LlmResponseError(
                "La sortie du LLM ne respecte pas le schéma attendu."
            )

        intent = data["intent"]
        confidence = data["confidence"]
        destination = data["destination"]
        uses_memory = data["uses_memory"]
        explanation = data["explanation"]
        if intent not in {*VALID_INTENTS, "unknown"}:
            raise LlmResponseError(f"Intention LLM interdite: {intent!r}.")
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise LlmResponseError("La confiance LLM doit être numérique.")
        if not 0.0 <= float(confidence) <= 1.0:
            raise LlmResponseError("La confiance LLM doit être comprise entre 0 et 1.")
        if destination is not None and destination not in self.allowed_destinations:
            raise LlmResponseError(f"Destination LLM interdite: {destination!r}.")
        if not isinstance(uses_memory, bool):
            raise LlmResponseError("uses_memory doit être booléen.")
        if not isinstance(explanation, str) or len(explanation) > 240:
            raise LlmResponseError("L'explication LLM est invalide ou trop longue.")
        return LlmInterpretation(
            intent=intent,
            confidence=float(confidence),
            destination=destination,
            uses_memory=uses_memory,
            explanation=explanation,
        )

    def _response_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "intent": {
                    "type": "string",
                    "enum": [*VALID_INTENTS, "unknown"],
                },
                "destination": {
                    "anyOf": [
                        {"type": "string", "enum": list(self.allowed_destinations)},
                        {"type": "null"},
                    ]
                },
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "uses_memory": {"type": "boolean"},
                "explanation": {"type": "string", "maxLength": 240},
            },
            "required": [
                "intent",
                "destination",
                "confidence",
                "uses_memory",
                "explanation",
            ],
            "additionalProperties": False,
        }

    def _system_prompt(self, schema: dict[str, Any]) -> str:
        return (
            "Tu es uniquement un analyseur de commandes pour un robot mobile. "
            "Tu n'exécutes rien. Les seules intentions sont navigate, stop, report "
            "et unknown. Les seules destinations autorisées sont: "
            f"{', '.join(self.allowed_destinations)}. "
            "Une ancienne commande peut résoudre une référence explicite comme "
            "'refais la dernière commande' ou 'retourne là-bas'. Dans ce cas "
            "seulement, "
            "mets uses_memory à true. N'invente jamais de destination. Une demande "
            "hors domaine vaut unknown. Réponds exclusivement selon ce schéma JSON: "
            f"{json.dumps(schema, ensure_ascii=False)}"
        )

    @staticmethod
    def _user_prompt(text: str, history: Sequence[CommandRecord]) -> str:
        safe_history = [
            {
                "text": item.text,
                "intent": item.intent,
                "destination": item.destination,
            }
            for item in history
        ]
        return json.dumps(
            {"historique_accepte": safe_history, "commande_actuelle": text},
            ensure_ascii=False,
        )
