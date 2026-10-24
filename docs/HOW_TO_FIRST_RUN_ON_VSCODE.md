# First run dans VS Code

Ce guide part d’un PC Windows et sépare deux objectifs :

1. lancer immédiatement le pipeline NLP avec le LLM local et sa mémoire ;
2. lancer ensuite la simulation complète Gazebo/Nav2 sous Ubuntu 22.04.

Le premier objectif fonctionne directement sous Windows. Le second exige ROS 2 Humble et doit être exécuté sous Ubuntu 22.04, idéalement en installation native. WSL2 convient au développement, mais l’affichage et l’accélération de Gazebo doivent être testés avant une démonstration.

## 1. Installer les prérequis Windows

Installez :

- [Git](https://git-scm.com/download/win) ;
- [Visual Studio Code](https://code.visualstudio.com/download) ;
- Python 3.10 64 bits ;
- [Ollama](https://ollama.com/download/windows).

Python 3.10 est recommandé parce qu’il correspond à Ubuntu 22.04 et ROS 2 Humble. Pendant l’installation Python, activez l’option d’ajout au `PATH`.

Dans PowerShell, vérifiez :

```powershell
git --version
code --version
py -3.10 --version
ollama --version
```

## 2. Cloner et ouvrir le projet

Dans PowerShell :

```powershell
cd $HOME\Documents
git clone https://github.com/yayaSB/NLP-Robot-Commander.git
cd NLP-Robot-Commander
code .
```

Dans VS Code, acceptez les extensions recommandées. Les deux extensions utiles sont **Python** et **WSL**, toutes deux publiées par Microsoft.

## 3. Créer l’environnement Python

Ouvrez le terminal intégré avec **Terminal > New Terminal**, puis exécutez :

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

Si PowerShell bloque uniquement le script d’activation, autorisez-le pour ce processus, puis recommencez :

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Choisissez ensuite l’interpréteur dans VS Code :

1. ouvrez la palette avec `Ctrl+Shift+P` ;
2. lancez **Python: Select Interpreter** ;
3. sélectionnez `.venv\Scripts\python.exe`.

## 4. Préparer le LLM local

Ollama doit tourner sur le PC. L’application Windows le démarre généralement elle-même. Vérifiez :

```powershell
ollama list
```

Si la connexion locale échoue, gardez un deuxième terminal ouvert avec :

```powershell
ollama serve
```

Téléchargez une seule fois le modèle multilingue léger :

```powershell
ollama pull llama3.2:1b
ollama list
```

Le modèle Ollama est conservé sur le PC, pas dans le dépôt GitHub. Le projet appelle seulement `http://127.0.0.1:11434` et n’a besoin d’aucune clé API.

## 5. Premier lancement dans VS Code

La configuration est déjà livrée dans `.vscode/launch.json`.

1. ouvrez **Run and Debug** avec `Ctrl+Shift+D` ;
2. choisissez **NLP demo: LLM + memory** ;
3. appuyez sur `F5`.

Vous pouvez aussi utiliser le terminal :

```powershell
python .\scripts\demo_pipeline.py `
  --llm `
  --llm-model llama3.2:1b `
  --llm-timeout 60 `
  --memory-db .\artifacts\runtime\command_memory.sqlite3
```

Entrez ces deux commandes dans cet ordre :

```text
Va dans la cuisine
Refais la dernière commande
```

Pour la seconde commande, vérifiez dans le JSON :

```json
{
  "accepted": true,
  "intent": "navigate",
  "destination": "cuisine",
  "source": "memory_rules",
  "memory_used": true
}
```

Tapez `quit` pour fermer. Pour vider l’historique, ajoutez `--clear-memory`. La base SQLite est locale, limitée à 200 commandes acceptées et ignorée par Git.

## 6. Ajouter DistilBERT comme secours

Le poids DistilBERT dépasse la limite standard de GitHub, donc un clone neuf ne contient pas le dossier final du modèle. Deux possibilités existent.

### Copier le modèle déjà entraîné

Copiez le dossier complet dans :

```text
models/distilbert-robot-commander-3intents
```

Il doit notamment contenir `config.json`, le tokenizer et `model.safetensors`.

### Réentraîner le modèle

Dans le terminal VS Code activé :

```powershell
python .\scripts\train_intent_classifier.py `
  --output-dir .\models\distilbert-robot-commander-3intents `
  --artifacts-dir .\artifacts\training_3intents `
  --epochs 12 --batch-size 8 --seed 42
```

L’entraînement télécharge le modèle de base lors de la première exécution et peut être long sur CPU.

Une fois le dossier présent, sélectionnez dans **Run and Debug** :

```text
NLP demo: DistilBERT + LLM + memory
```

Commande équivalente :

```powershell
python .\scripts\demo_pipeline.py `
  --model .\models\distilbert-robot-commander-3intents `
  --llm --llm-model llama3.2:1b `
  --llm-timeout 60 `
  --memory-db .\artifacts\runtime\command_memory.sqlite3
```

Si Ollama est arrêté, le champ `source` devient `classifier_fallback`. Pour refuser toute commande plutôt que d’utiliser ce secours, ajoutez `--no-llm-fallback`.

## 7. Lancer les tests depuis VS Code

Utilisez **Terminal > Run Task > NLP: run all tests**, ou :

```powershell
python -m pytest -q --basetemp .pytest-tmp
python -m compileall -q scripts src tests
```

Le résultat de référence après l’ajout du LLM est `51 passed`.

## 8. Comprendre ce qui est appris

Le LLM ne réentraîne pas ses poids en direct. Le projet réalise un apprentissage contextuel contrôlé :

- seules les commandes acceptées sont enregistrées ;
- les 8 commandes les plus récentes sont données au LLM ;
- une référence explicite telle que `refais`, `dernière commande` ou `retourne là-bas` réutilise ce contexte directement depuis SQLite ;
- toute destination finale doit encore appartenir à `waypoints.yaml` ;
- le LLM ne possède aucun accès direct à ROS 2 ou Nav2.

Un arrêt explicite contourne l’attente du LLM et annule logiquement toute interprétation plus ancienne encore en cours.

## 9. Simulation complète dans VS Code sous Ubuntu 22.04

Installez ROS 2 Humble, Nav2, TurtleBot3 et Gazebo selon leurs documentations officielles. Clonez ensuite le dépôt dans Ubuntu et ouvrez-le avec VS Code depuis ce système. Sous WSL2, ouvrez le dossier avec **WSL: Open Folder in WSL**.

Dans le terminal Ubuntu de VS Code :

```bash
source /opt/ros/humble/setup.bash
cd ~/NLP-Robot-Commander
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
rosdep install --from-paths src --ignore-src -r -y
colcon build --packages-select nlp_robot_commander --symlink-install
source install/setup.bash
```

Installez et démarrez Ollama sur cette même machine Ubuntu, puis :

```bash
ollama pull llama3.2:1b
ollama serve
```

Dans un nouveau terminal Ubuntu correctement sourcé :

```bash
export TURTLEBOT3_MODEL=burger
source /opt/ros/humble/setup.bash
source ~/NLP-Robot-Commander/install/setup.bash
cd ~/NLP-Robot-Commander
ros2 launch nlp_robot_commander simulation.launch.py \
  model_path:="$(realpath models/distilbert-robot-commander-3intents)" \
  llm_enabled:=true \
  llm_model:=llama3.2:1b \
  map:=/chemin/absolu/vers/map.yaml
```

Dans un troisième terminal :

```bash
source /opt/ros/humble/setup.bash
source ~/NLP-Robot-Commander/install/setup.bash
ros2 run nlp_robot_commander terminal_client
```

Pour afficher les décisions et résultats :

```bash
ros2 topic echo /nlp_commander/status
```

Avant la première navigation, placez la pose initiale du robot dans RViz2 et remplacez les coordonnées d’exemple de `src/nlp_robot_commander/config/waypoints.yaml` par des poses libres mesurées sur votre carte.

## 10. Dépannage rapide

| Erreur | Correction |
|---|---|
| `No module named ...` | Vérifiez l’interpréteur `.venv`, puis réinstallez `requirements-dev.txt`. |
| Ollama refuse la connexion | Démarrez l’application ou `ollama serve`, puis testez `ollama list`. |
| Modèle Ollama absent | Exécutez `ollama pull llama3.2:1b`. |
| Premier appel LLM expiré | Le chargement à froid peut être lent ; gardez `--llm-timeout 60` pour le premier lancement. |
| `Checkpoint introuvable` | Copiez ou entraînez DistilBERT, ou lancez la configuration sans DistilBERT. |
| `LLM_UNAVAILABLE` | Vérifiez Ollama ; retirez `--no-llm-fallback` si le secours est souhaité. |
| `UNKNOWN_DESTINATION` | Utilisez un waypoint de `waypoints.yaml` ou ajoutez-y un alias unique. |
| `action_server_unavailable` | Attendez que Nav2 soit actif et vérifiez `/navigate_to_pose`. |
| Aucun mouvement dans Gazebo | Initialisez la pose dans RViz2, contrôlez la carte et les waypoints. |

Pour la validation ROS 2 complète et la collecte des preuves, poursuivez avec [`ACTIONS_MANUELLES.md`](ACTIONS_MANUELLES.md).
