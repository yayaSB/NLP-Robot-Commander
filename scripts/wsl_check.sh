#!/usr/bin/env bash
set -u

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ERRORS=0
WARNINGS=0

ok() {
  printf '[OK] %s\n' "$1"
}

warn() {
  printf '[AVERTISSEMENT] %s\n' "$1"
  WARNINGS=$((WARNINGS + 1))
}

fail() {
  printf '[ERREUR] %s\n' "$1"
  ERRORS=$((ERRORS + 1))
}

has_command() {
  command -v "$1" >/dev/null 2>&1
}

printf 'Diagnostic WSL — NLP Robot Commander\n'
printf 'Projet: %s\n\n' "$PROJECT_ROOT"

if grep -qi microsoft /proc/version 2>/dev/null; then
  ok 'Exécution dans WSL détectée.'
else
  fail 'Ce script doit être exécuté dans WSL2.'
fi

if uname -r | grep -qi 'wsl2\|microsoft-standard'; then
  ok 'Noyau WSL2 détecté.'
else
  fail 'WSL2 non détecté. Vérifiez `wsl --list --verbose` dans PowerShell.'
fi

if [[ -r /etc/os-release ]]; then
  # shellcheck disable=SC1091
  source /etc/os-release
  if [[ "${ID:-}" == 'ubuntu' && "${VERSION_ID:-}" == '22.04' ]]; then
    ok 'Ubuntu 22.04 détecté.'
  else
    fail "Ubuntu 22.04 requis; système détecté: ${PRETTY_NAME:-inconnu}."
  fi
else
  fail '/etc/os-release est introuvable.'
fi

if [[ "$PROJECT_ROOT" == /mnt/* ]]; then
  fail 'Le dépôt est sous /mnt. Clonez-le dans ~/projects pour éviter les problèmes de performances et de permissions.'
else
  ok 'Le dépôt est stocké dans le système de fichiers Linux.'
fi

if [[ "$(ps -p 1 -o comm= 2>/dev/null | tr -d ' ')" == 'systemd' ]]; then
  ok 'systemd est actif.'
else
  warn 'systemd est inactif; le service Ollama devra être lancé manuellement.'
fi

for executable in git curl python3 pip3 ros2 colcon rosdep; do
  if has_command "$executable"; then
    ok "$executable est disponible."
  else
    fail "$executable est absent. Relancez scripts/wsl_setup.sh."
  fi
done

if [[ -f /opt/ros/humble/setup.bash ]]; then
  set +u
  # shellcheck disable=SC1091
  source /opt/ros/humble/setup.bash
  set -u
  if [[ "${ROS_DISTRO:-}" == 'humble' ]]; then
    ok 'ROS 2 Humble est correctement sourcé.'
  else
    fail 'ROS_DISTRO ne vaut pas humble.'
  fi
else
  fail '/opt/ros/humble/setup.bash est absent.'
fi

for package in nav2_bringup turtlebot3_gazebo turtlebot3_navigation2; do
  if has_command ros2 && ros2 pkg prefix "$package" >/dev/null 2>&1; then
    ok "Package ROS 2 présent: $package."
  else
    fail "Package ROS 2 absent: $package."
  fi
done

if [[ -x "$PROJECT_ROOT/.venv/bin/python" ]]; then
  ok 'Environnement Python Linux .venv présent.'
  if "$PROJECT_ROOT/.venv/bin/python" -c 'import rclpy, torch, transformers, pandas, yaml' >/dev/null 2>&1; then
    ok 'Imports Python ROS 2 et NLP réussis.'
  else
    fail 'Un import Python ROS 2/NLP échoue dans .venv.'
  fi
else
  fail '.venv Linux absent. Relancez scripts/wsl_setup.sh.'
fi

if [[ -f "$PROJECT_ROOT/install/setup.bash" ]]; then
  set +u
  # shellcheck disable=SC1091
  source "$PROJECT_ROOT/install/setup.bash"
  set -u
  if ros2 pkg prefix nlp_robot_commander >/dev/null 2>&1; then
    ok 'Workspace colcon construit et package détecté.'
  else
    fail 'Le package construit n’est pas visible par ROS 2.'
  fi
else
  fail 'Workspace non construit. Exécutez scripts/wsl_build.sh.'
fi

MODEL_DIR="$PROJECT_ROOT/models/distilbert-robot-commander-3intents"
if [[ -f "$MODEL_DIR/config.json" && -f "$MODEL_DIR/model.safetensors" ]]; then
  ok 'Checkpoint DistilBERT local présent.'
else
  warn 'Checkpoint DistilBERT absent; copiez-le depuis Windows ou entraînez-le dans WSL.'
fi

if has_command ollama; then
  ok 'Ollama est installé dans WSL.'
  if pgrep -x ollama >/dev/null 2>&1; then
    ok 'Processus Ollama exécuté dans WSL.'
  else
    warn 'Aucun processus Ollama WSL détecté; arrêtez Ollama sous Windows et démarrez-le dans WSL.'
  fi
  if curl -fsS --max-time 3 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    ok 'API Ollama locale accessible.'
    if ollama list 2>/dev/null | awk 'NR > 1 {print $1}' | grep -Fxq 'llama3.2:1b'; then
      ok 'Modèle Ollama llama3.2:1b présent.'
    else
      warn 'Modèle llama3.2:1b absent; exécutez `ollama pull llama3.2:1b`.'
    fi
  else
    warn 'Ollama ne répond pas sur 127.0.0.1:11434.'
  fi
else
  warn 'Ollama est absent dans WSL.'
fi

if [[ -n "${WAYLAND_DISPLAY:-}" || -n "${DISPLAY:-}" ]]; then
  ok 'Affichage WSLg détecté pour RViz2/Gazebo.'
else
  warn 'Aucun affichage WSLg détecté; RViz2 et Gazebo ne pourront pas ouvrir leur fenêtre.'
fi

printf '\nRésumé: %d erreur(s), %d avertissement(s).\n' "$ERRORS" "$WARNINGS"
if (( ERRORS > 0 )); then
  exit 1
fi

printf 'Environnement essentiel prêt. Les avertissements doivent être traités avant la démonstration complète.\n'
