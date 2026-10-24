#!/usr/bin/env bash

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  printf 'Ce fichier doit être sourcé: source scripts/wsl_env.sh\n' >&2
  exit 1
fi

NLP_ROBOT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -f /opt/ros/humble/setup.bash ]]; then
  printf 'ROS 2 Humble absent. Exécutez scripts/wsl_setup.sh.\n' >&2
  return 1
fi
if [[ ! -f "$NLP_ROBOT_ROOT/.venv/bin/activate" ]]; then
  printf '.venv Linux absent. Exécutez scripts/wsl_setup.sh.\n' >&2
  return 1
fi
if [[ ! -f "$NLP_ROBOT_ROOT/install/setup.bash" ]]; then
  printf 'Workspace non construit. Exécutez scripts/wsl_build.sh.\n' >&2
  return 1
fi

# shellcheck disable=SC1091
source /opt/ros/humble/setup.bash
# shellcheck disable=SC1091
source "$NLP_ROBOT_ROOT/.venv/bin/activate"
# shellcheck disable=SC1091
source "$NLP_ROBOT_ROOT/install/setup.bash"
export TURTLEBOT3_MODEL="${TURTLEBOT3_MODEL:-burger}"

printf 'Environnement actif: ROS_DISTRO=%s, TURTLEBOT3_MODEL=%s\n' \
  "${ROS_DISTRO:-inconnu}" "$TURTLEBOT3_MODEL"
