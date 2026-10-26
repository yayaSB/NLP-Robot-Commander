#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -f /opt/ros/humble/setup.bash ]]; then
  printf 'ROS 2 Humble absent. Exécutez d’abord scripts/wsl_setup.sh.\n' >&2
  exit 1
fi
if [[ ! -x "$PROJECT_ROOT/.venv/bin/python" ]]; then
  printf '.venv Linux absent. Exécutez d’abord scripts/wsl_setup.sh.\n' >&2
  exit 1
fi

set +u
# shellcheck disable=SC1091
source /opt/ros/humble/setup.bash
# shellcheck disable=SC1091
source "$PROJECT_ROOT/.venv/bin/activate"
set -u

cd "$PROJECT_ROOT"
rosdep install --from-paths src --ignore-src -r -y --rosdistro humble
python -m colcon build --packages-select nlp_robot_commander --symlink-install
set +u
# shellcheck disable=SC1091
source "$PROJECT_ROOT/install/setup.bash"
set -u
python -m pytest -q --basetemp "$PROJECT_ROOT/.pytest-wsl"
python -m compileall -q scripts src tests

printf 'Build et tests terminés. Package: %s\n' "$(ros2 pkg prefix nlp_robot_commander)"
