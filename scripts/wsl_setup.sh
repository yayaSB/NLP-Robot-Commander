#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OLLAMA_MODEL="${OLLAMA_MODEL:-llama3.2:1b}"
SKIP_OLLAMA=false

if [[ "${1:-}" == '--skip-ollama' ]]; then
  SKIP_OLLAMA=true
elif [[ $# -gt 0 ]]; then
  printf 'Usage: bash scripts/wsl_setup.sh [--skip-ollama]\n' >&2
  exit 2
fi

if ! grep -qi microsoft /proc/version 2>/dev/null; then
  printf 'Erreur: exécutez ce script dans WSL2.\n' >&2
  exit 1
fi

if [[ ! -r /etc/os-release ]]; then
  printf 'Erreur: /etc/os-release est introuvable.\n' >&2
  exit 1
fi

# shellcheck disable=SC1091
source /etc/os-release
if [[ "${ID:-}" != 'ubuntu' || "${VERSION_ID:-}" != '22.04' ]]; then
  printf 'Erreur: Ubuntu 22.04 est requis; système détecté: %s.\n' "${PRETTY_NAME:-inconnu}" >&2
  exit 1
fi

if [[ "$PROJECT_ROOT" == /mnt/* ]]; then
  printf 'Erreur: le dépôt est sous /mnt. Clonez-le dans ~/projects puis relancez ce script.\n' >&2
  exit 1
fi

printf '\n[1/7] Prérequis Ubuntu\n'
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  build-essential \
  ca-certificates \
  curl \
  git \
  locales \
  python3-pip \
  python3-venv \
  software-properties-common
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8
sudo add-apt-repository -y universe

printf '\n[2/7] Dépôt officiel ROS 2\n'
if ! dpkg-query -W -f='${Status}' ros2-apt-source 2>/dev/null | grep -q 'install ok installed'; then
  ROS_APT_SOURCE_VERSION="$(
    curl -fsSL https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest \
      | awk -F'"' '/tag_name/ && !version {version=$4} END {print version}'
  )"
  if [[ -z "$ROS_APT_SOURCE_VERSION" ]]; then
    printf 'Erreur: impossible de déterminer la version de ros2-apt-source.\n' >&2
    exit 1
  fi
  ROS_APT_SOURCE_DEB="/tmp/ros2-apt-source.deb"
  curl -fL \
    -o "$ROS_APT_SOURCE_DEB" \
    "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ROS_APT_SOURCE_VERSION}/ros2-apt-source_${ROS_APT_SOURCE_VERSION}.jammy_all.deb"
  sudo dpkg -i "$ROS_APT_SOURCE_DEB"
fi

printf '\n[3/7] ROS 2 Humble, Nav2, Gazebo et TurtleBot3\n'
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  python3-colcon-common-extensions \
  python3-rosdep \
  ros-dev-tools \
  ros-humble-desktop \
  ros-humble-gazebo-ros-pkgs \
  ros-humble-navigation2 \
  ros-humble-nav2-bringup \
  ros-humble-turtlebot3 \
  ros-humble-turtlebot3-gazebo \
  ros-humble-turtlebot3-navigation2

set +u
# shellcheck disable=SC1091
source /opt/ros/humble/setup.bash
set -u

printf '\n[4/7] rosdep\n'
if [[ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]]; then
  sudo rosdep init
fi
rosdep update
rosdep install --from-paths "$PROJECT_ROOT/src" --ignore-src -r -y --rosdistro humble

printf '\n[5/7] Environnement Python Linux\n'
if [[ ! -d "$PROJECT_ROOT/.venv" ]]; then
  python3 -m venv --system-site-packages "$PROJECT_ROOT/.venv"
fi
if ! grep -Eq '^include-system-site-packages = true$' "$PROJECT_ROOT/.venv/pyvenv.cfg"; then
  printf 'Erreur: .venv existe sans accès aux paquets ROS 2. Supprimez uniquement .venv puis relancez.\n' >&2
  exit 1
fi
set +u
# shellcheck disable=SC1091
source "$PROJECT_ROOT/.venv/bin/activate"
set -u
python -m pip install --upgrade pip
python -m pip install -r "$PROJECT_ROOT/requirements-dev.txt"

printf '\n[6/7] Build et tests\n'
cd "$PROJECT_ROOT"
colcon build --packages-select nlp_robot_commander --symlink-install
set +u
# shellcheck disable=SC1091
source "$PROJECT_ROOT/install/setup.bash"
set -u
python -m pytest -q --basetemp "$PROJECT_ROOT/.pytest-wsl"
python -m compileall -q scripts src tests

printf '\n[7/7] Ollama local dans WSL\n'
if [[ "$SKIP_OLLAMA" == false ]]; then
  if ! command -v ollama >/dev/null 2>&1; then
    OLLAMA_INSTALLER="/tmp/ollama-install.sh"
    curl -fsSL https://ollama.com/install.sh -o "$OLLAMA_INSTALLER"
    sh "$OLLAMA_INSTALLER"
  fi

  if [[ "$(ps -p 1 -o comm= | tr -d ' ')" == 'systemd' ]] \
    && systemctl cat ollama.service >/dev/null 2>&1; then
    sudo systemctl enable --now ollama
  elif ! pgrep -x ollama >/dev/null 2>&1; then
    mkdir -p "$PROJECT_ROOT/artifacts/runtime"
    nohup ollama serve >"$PROJECT_ROOT/artifacts/runtime/ollama.log" 2>&1 &
  fi

  for _ in $(seq 1 30); do
    if curl -fsS --max-time 2 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
  if ! curl -fsS --max-time 2 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    printf 'Erreur: Ollama est installé mais son API ne répond pas. Lancez `ollama serve`.\n' >&2
    exit 1
  fi
  if ! pgrep -x ollama >/dev/null 2>&1; then
    printf 'Erreur: l’API répond, mais Ollama ne tourne pas dans WSL. Fermez Ollama sous Windows puis relancez.\n' >&2
    exit 1
  fi
  ollama pull "$OLLAMA_MODEL"
else
  printf 'Installation Ollama ignorée (--skip-ollama).\n'
fi

printf '\nInstallation terminée.\n'
printf '1. Préparez le checkpoint DistilBERT (voir docs/HOW_TO_FIRST_RUN_ON_VSCODE.md).\n'
printf '2. Exécutez: bash scripts/wsl_check.sh\n'
printf '3. Dans chaque terminal ROS: source scripts/wsl_env.sh\n'
printf '4. Lancez la démo: bash scripts/wsl_run_demo.sh --clear-memory\n'
printf '5. Lancez la simulation: bash scripts/wsl_run_simulation.sh [map.yaml]\n'
