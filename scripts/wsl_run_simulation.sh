#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL_DIR="${NLP_MODEL_PATH:-$PROJECT_ROOT/models/distilbert-robot-commander-3intents}"
OLLAMA_MODEL="${OLLAMA_MODEL:-llama3.2:1b}"
MAP_PATH="${1:-}"
WORLD_PATH="${2:-}"

if [[ ! -f /opt/ros/humble/setup.bash ]]; then
  printf 'ROS 2 Humble absent. Exécutez scripts/wsl_setup.sh.\n' >&2
  exit 1
fi
if [[ ! -f "$PROJECT_ROOT/install/setup.bash" ]]; then
  printf 'Workspace non construit. Exécutez scripts/wsl_build.sh.\n' >&2
  exit 1
fi
if [[ ! -f "$PROJECT_ROOT/.venv/bin/activate" ]]; then
  printf '.venv Linux absent. Exécutez scripts/wsl_setup.sh.\n' >&2
  exit 1
fi
if [[ ! -f "$MODEL_DIR/config.json" ]]; then
  printf 'Checkpoint DistilBERT absent: %s\n' "$MODEL_DIR" >&2
  printf 'Copiez-le ou entraînez-le avant la simulation complète.\n' >&2
  exit 1
fi
if [[ -z "${WAYLAND_DISPLAY:-}" && -z "${DISPLAY:-}" ]]; then
  printf 'Affichage WSLg absent; Gazebo/RViz2 ne peuvent pas démarrer.\n' >&2
  exit 1
fi
if ! pgrep -x ollama >/dev/null 2>&1; then
  printf 'Aucun processus Ollama dans WSL. Fermez Ollama sous Windows et lancez `ollama serve` dans WSL.\n' >&2
  exit 1
fi
if ! curl -fsS --max-time 3 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  printf 'Ollama ne répond pas dans WSL. Lancez `ollama serve`.\n' >&2
  exit 1
fi
if [[ -n "$MAP_PATH" && ! -f "$MAP_PATH" ]]; then
  printf 'Carte introuvable: %s\n' "$MAP_PATH" >&2
  exit 1
fi
if [[ -n "$WORLD_PATH" && ! -f "$WORLD_PATH" ]]; then
  printf 'Monde Gazebo introuvable: %s\n' "$WORLD_PATH" >&2
  exit 1
fi
if [[ -n "$MAP_PATH" && -z "$WORLD_PATH" ]] \
  || [[ -z "$MAP_PATH" && -n "$WORLD_PATH" ]]; then
  printf 'Une carte et son monde Gazebo doivent être fournis ensemble.\n' >&2
  printf 'Usage: bash scripts/wsl_run_simulation.sh [map.yaml monde.world]\n' >&2
  exit 2
fi

set +u
# shellcheck disable=SC1091
source /opt/ros/humble/setup.bash
# shellcheck disable=SC1091
source "$PROJECT_ROOT/.venv/bin/activate"
# shellcheck disable=SC1091
source "$PROJECT_ROOT/install/setup.bash"
set -u
export TURTLEBOT3_MODEL="${TURTLEBOT3_MODEL:-burger}"

LAUNCH_ARGS=(
  "model_path:=$(realpath "$MODEL_DIR")"
  'llm_enabled:=true'
  "llm_model:=$OLLAMA_MODEL"
  'llm_timeout_sec:=60.0'
  "auto_initial_pose:=${AUTO_INITIAL_POSE:-true}"
  "initial_x:=${INITIAL_X:--4.0}"
  "initial_y:=${INITIAL_Y:-0.0}"
  "initial_yaw:=${INITIAL_YAW:-0.0}"
)
if [[ -n "$MAP_PATH" ]]; then
  LAUNCH_ARGS+=("map:=$(realpath "$MAP_PATH")")
  LAUNCH_ARGS+=("world:=$(realpath "$WORLD_PATH")")
fi

cd "$PROJECT_ROOT"
exec ros2 launch nlp_robot_commander simulation.launch.py "${LAUNCH_ARGS[@]}"
