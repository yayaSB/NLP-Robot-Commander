#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL_DIR="${NLP_MODEL_PATH:-$PROJECT_ROOT/models/distilbert-robot-commander-3intents}"
OLLAMA_MODEL="${OLLAMA_MODEL:-llama3.2:1b}"
MEMORY_DB="$PROJECT_ROOT/artifacts/runtime/command_memory.sqlite3"

if [[ ! -x "$PROJECT_ROOT/.venv/bin/python" ]]; then
  printf '.venv Linux absent. Exécutez scripts/wsl_setup.sh.\n' >&2
  exit 1
fi
if ! pgrep -x ollama >/dev/null 2>&1; then
  printf 'Aucun processus Ollama dans WSL. Fermez Ollama sous Windows et lancez `ollama serve` dans WSL.\n' >&2
  exit 1
fi
if ! curl -fsS --max-time 3 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  printf 'Ollama ne répond pas dans WSL. Lancez `ollama serve` puis recommencez.\n' >&2
  exit 1
fi

set +u
# shellcheck disable=SC1091
source "$PROJECT_ROOT/.venv/bin/activate"
set -u
cd "$PROJECT_ROOT"
mkdir -p artifacts/runtime

ARGS=(
  --llm
  --llm-model "$OLLAMA_MODEL"
  --llm-timeout 60
  --memory-db "$MEMORY_DB"
)
if [[ -f "$MODEL_DIR/config.json" ]]; then
  ARGS=(--model "$MODEL_DIR" "${ARGS[@]}")
else
  printf 'Avertissement: checkpoint absent; classifieur lexical utilisé en secours.\n' >&2
fi

exec python scripts/demo_pipeline.py "${ARGS[@]}" "$@"
