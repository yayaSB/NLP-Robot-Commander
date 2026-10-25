# Guide utilisateur

L’environnement de référence est WSL2 avec Ubuntu 22.04. Effectuez d’abord le
bootstrap et le diagnostic décrits dans
[`HOW_TO_FIRST_RUN_ON_VSCODE.md`](HOW_TO_FIRST_RUN_ON_VSCODE.md) :

```bash
bash scripts/wsl_setup.sh
bash scripts/wsl_check.sh
```

## Préparer le modèle

Créez un environnement Python, installez `requirements-dev.txt`, exécutez l’audit du dataset puis entraînez le checkpoint. Le chemin résultant doit contenir `config.json`, les fichiers du tokenizer et les poids du modèle.

Testez d’abord le pipeline local dans WSL :

```bash
bash scripts/wsl_run_demo.sh --clear-memory
```

Exemples attendus :

- `Rends-toi dans la cuisine` → navigation acceptée vers `cuisine` ;
- `Arrête-toi immédiatement` → arrêt prioritaire ;
- `Où te trouves-tu ?` → rapport accepté ;
- `Ne va pas dans la cuisine` → refus `NEGATED_COMMAND` ;
- `Va dans la cuisine puis dans le laboratoire` → refus `SEQUENTIAL_COMMAND`.

## Activer la mémoire LLM locale

Le bootstrap installe Ollama dans WSL. Vérifiez-le avec :

```bash
ollama pull llama3.2:1b
ollama serve
```

Si le service Ollama tourne déjà, la seconde commande est inutile. Lancez :

```bash
bash scripts/wsl_run_demo.sh
```

Entrez `Va dans la cuisine`, puis `Refais la dernière commande`. L’historique se trouve par défaut dans `~/.local/share/nlp_robot_commander/command_memory.sqlite3`. `--clear-memory` l’efface au démarrage. Il ne contient que les commandes acceptées et reste limité à 200 lignes.

## Préparer ROS 2

Sous Ubuntu 22.04 dans WSL :

```bash
bash scripts/wsl_build.sh
source scripts/wsl_env.sh
```

Les poses de `waypoints.yaml` sont libres sur la carte TurtleBot3 par défaut.
Adaptez-les si vous utilisez une autre carte. Chaque entrée exige `x`, `y`,
`yaw` et une liste d’alias sans ambiguïté.

## Démarrer

```bash
bash scripts/wsl_run_simulation.sh /chemin/vers/map.yaml
```

Sans argument, le script utilise la carte TurtleBot3 et initialise
automatiquement AMCL à la pose du spawn Gazebo. Attendez `Localisation
initialisée` avant la première commande.

Puis, dans deux terminaux WSL séparés :

```bash
source scripts/wsl_env.sh
ros2 run nlp_robot_commander terminal_client
```

```bash
source scripts/wsl_env.sh
ros2 topic echo /nlp_commander/status
```

L’entrée micro est optionnelle : installez `requirements-audio.txt`, vérifiez le microphone puis lancez `ros2 run nlp_robot_commander microphone_client`.

## Lire les statuts

Chaque message est un objet JSON avec un champ `event`. `command_parsed` indique acceptation, intention, confiance, destination, `source`, `memory_used` et éventuel code d’erreur. Pour l’arrêt, attendez `stop_confirmed`; `cancellation_requested` ne suffit pas. Pour la position, n’utilisez que `position_report`; les événements `position_stale` et `position_unavailable` signifient qu’aucune pose actuelle fiable n’est disponible.

## Dépannage

- `model_path absolu requis` : passez un chemin absolu au lancement.
- `Checkpoint invalide` : réentraînez le modèle ou vérifiez tous ses fichiers.
- `action_server_unavailable` : activez Nav2 et contrôlez `/navigate_to_pose`.
- `localization_unavailable` : attendez l'initialisation automatique ou utilisez **2D Pose Estimate** dans RViz2.
- `position_unavailable` : vérifiez les frames `map` et `base_link` ainsi que la localisation.
- `LLM_UNAVAILABLE` : démarrez Ollama, vérifiez `ollama list`, ou activez le secours avec `llm_fallback_to_classifier: true`.
- `source: classifier_fallback` : la commande a été traitée sans LLM, car le secours explicitement configuré a été utilisé.
- But refusé : contrôlez la carte, le lifecycle Nav2, la pose initiale et les costmaps.
