import json

import pytest

from nlp_robot_commander.llm_interpreter import (
    LlmResponseError,
    OllamaLlmInterpreter,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_ollama_request_uses_schema_and_parses_safe_result():
    captured = {}

    def opener(request, timeout):
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        content = {
            "intent": "navigate",
            "destination": "cuisine",
            "confidence": 0.93,
            "uses_memory": True,
            "explanation": "Référence à la commande précédente.",
        }
        return FakeResponse({"message": {"content": json.dumps(content)}})

    interpreter = OllamaLlmInterpreter(
        ("cuisine", "salon"), timeout_sec=3.0, opener=opener
    )
    result = interpreter.interpret("Retourne là-bas", [])

    assert result.intent == "navigate"
    assert result.destination == "cuisine"
    assert result.uses_memory
    assert captured["body"]["stream"] is False
    assert captured["body"]["options"]["temperature"] == 0
    assert captured["body"]["format"]["additionalProperties"] is False
    assert captured["timeout"] == 3.0


def test_ollama_rejects_destination_outside_allowlist():
    def opener(_request, _timeout=None, **_kwargs):
        content = {
            "intent": "navigate",
            "destination": "garage",
            "confidence": 0.99,
            "uses_memory": False,
            "explanation": "Destination supposée.",
        }
        return FakeResponse({"message": {"content": json.dumps(content)}})

    interpreter = OllamaLlmInterpreter(("cuisine",), opener=opener)

    with pytest.raises(LlmResponseError, match="Destination LLM interdite"):
        interpreter.interpret("Va au garage", [])


@pytest.mark.parametrize(
    "endpoint",
    ["https://127.0.0.1:11434", "http://example.com:11434", "http://localhost/x"],
)
def test_ollama_endpoint_must_remain_local(endpoint):
    with pytest.raises(ValueError):
        OllamaLlmInterpreter(("cuisine",), endpoint=endpoint)
