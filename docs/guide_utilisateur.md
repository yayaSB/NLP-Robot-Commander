# Guide utilisateur

## Préparer le modèle

Créez un environnement Python, installez `requirements-dev.txt`, exécutez l’audit du dataset puis entraînez le checkpoint. Le chemin résultant doit contenir `config.json`, les fichiers du tokenizer et les poids du modèle.

Testez d’abord sans ROS 2 :

```bash
python scripts/demo_pipeline.py --model models/distilbert-robot-commander-3intents
```

Exemples attendus :

- `Rends-toi dans la cuisine` → navigation acceptée vers `cuisine` ;
- `Arrête-toi immédiatement` → arrêt prioritaire ;
- `Où te trouves-tu ?` → rapport accepté ;
- `Ne va pas dans la cuisine` → refus `NEGATED_COMMAND` ;
- `Va dans la cuisine puis dans le laboratoire` → refus `SEQUENTIAL_COMMAND`.

## Préparer ROS 2

Sous Ubuntu 22.04 :

```bash
source /opt/ros/humble/setup.bash
export TURTLEBOT3_MODEL=burger
colcon build --packages-select nlp_robot_commander --symlink-install
source install/setup.bash
```

Adaptez `waypoints.yaml` à la carte. Chaque entrée exige `x`, `y`, `yaw` et une liste d’alias sans ambiguïté.

## Démarrer

```bash
ros2 launch nlp_robot_commander simulation.launch.py \
  model_path:="$(realpath models/distilbert-robot-commander-3intents)" \
  map:=/chemin/vers/map.yaml
```

Puis :

```bash
ros2 run nlp_robot_commander terminal_client
ros2 topic echo /nlp_commander/status
```

L’entrée micro est optionnelle : installez `requirements-audio.txt`, vérifiez le microphone puis lancez `ros2 run nlp_robot_commander microphone_client`.

## Lire les statuts

Chaque message est un objet JSON avec un champ `event`. `command_parsed` indique acceptation, intention, confiance, destination et éventuel code d’erreur. Pour l’arrêt, attendez `stop_confirmed`; `cancellation_requested` ne suffit pas. Pour la position, n’utilisez que `position_report`; les événements `position_stale` et `position_unavailable` signifient qu’aucune pose actuelle fiable n’est disponible.

## Dépannage

- `model_path absolu requis` : passez un chemin absolu au lancement.
- `Checkpoint invalide` : réentraînez le modèle ou vérifiez tous ses fichiers.
- `action_server_unavailable` : activez Nav2 et contrôlez `/navigate_to_pose`.
- `position_unavailable` : vérifiez les frames `map` et `base_link` ainsi que la localisation.
- But refusé : contrôlez la carte, le lifecycle Nav2, la pose initiale et les costmaps.
