# Premier lancement complet — WSL2, Ubuntu 22.04 et VS Code

Ce guide place **tout le runtime du projet dans WSL2** : Python, notebook, DistilBERT, Ollama, SQLite, ROS 2 Humble, Nav2, Gazebo et RViz2. Windows conserve uniquement l’interface de VS Code et les fenêtres WSLg.

La configuration cible est volontairement stricte :

- WSL **version 2** ;
- Ubuntu **22.04 LTS (Jammy)** ;
- dépôt cloné dans le système de fichiers Linux, par exemple `~/projects/NLP-Robot-Commander` ;
- Python 3.10 fourni par Ubuntu 22.04 ;
- ROS 2 Humble installé par paquets Debian ;
- Ollama et `llama3.2:1b` installés dans WSL, pas utilisés depuis Windows.

> WSLg permet d’ouvrir Gazebo et RViz2, mais la fluidité graphique doit être testée avant la soutenance. Pour une démonstration critique, Ubuntu natif reste la solution la plus robuste.

## 1. Installer ou vérifier WSL2

Ouvrez **PowerShell en administrateur**.

Mettez WSL à jour :

```powershell
wsl --update
```

Affichez les distributions disponibles :

```powershell
wsl --list --online
```

Installez Ubuntu 22.04 si cette distribution n’existe pas encore :

```powershell
wsl --install -d Ubuntu-22.04
```

Redémarrez Windows si le programme le demande. Au premier lancement d’Ubuntu, créez le nom d’utilisateur et le mot de passe Linux. Le mot de passe ne s’affiche pas pendant la saisie : c’est normal.

Vérifiez ensuite depuis PowerShell :

```powershell
wsl --list --verbose
```

La ligne Ubuntu 22.04 doit afficher `VERSION 2`. Si elle affiche `1` :

```powershell
wsl --set-version Ubuntu-22.04 2
```

## 2. Vérifier Ubuntu et systemd

Ouvrez **Ubuntu 22.04** puis exécutez :

```bash
cat /etc/os-release
uname -r
ps -p 1 -o comm=
```

Résultats attendus :

- `VERSION_ID="22.04"` ;
- le noyau contient `microsoft-standard-WSL2` ;
- le processus 1 est `systemd`.

Si `systemd` n’est pas actif, ouvrez sa configuration :

```bash
sudo nano /etc/wsl.conf
```

Ajoutez :

```ini
[boot]
systemd=true
```

Enregistrez avec `Ctrl+O`, validez avec Entrée et quittez avec `Ctrl+X`. Revenez ensuite dans PowerShell :

```powershell
wsl --shutdown
```

Rouvrez Ubuntu et vérifiez de nouveau `ps -p 1 -o comm=`.

## 3. Cloner le dépôt dans Linux

Dans le terminal Ubuntu :

```bash
mkdir -p ~/projects
cd ~/projects
git clone https://github.com/yayaSB/NLP-Robot-Commander.git
cd NLP-Robot-Commander
```

N’utilisez pas `/mnt/c/Users/.../NLP` comme dossier de travail principal. Les builds `colcon`, les environnements Python et les nombreux petits fichiers sont plus rapides et plus fiables dans `/home/<utilisateur>`.

Vérifiez le chemin :

```bash
pwd
```

Il doit ressembler à :

```text
/home/votre_utilisateur/projects/NLP-Robot-Commander
```

## 4. Ouvrir le bon VS Code

Installez sous Windows les extensions **WSL**, **Python** et **Jupyter** de Microsoft. Depuis le terminal Ubuntu, dans le dépôt :

```bash
code .
```

La barre inférieure gauche de VS Code doit indiquer `WSL: Ubuntu-22.04`. Tous les nouveaux terminaux intégrés doivent afficher un shell Linux, jamais PowerShell.

Le dépôt fournit déjà :

- `.vscode/settings.json` pour utiliser `.venv/bin/python` ;
- `.vscode/tasks.json` pour l’installation, le diagnostic, le build, les tests et la simulation ;
- `.vscode/launch.json` pour les démonstrations NLP avec le débogueur Python.

## 5. Installer automatiquement toute la pile

Dans le terminal WSL ouvert à la racine du dépôt :

```bash
bash scripts/wsl_setup.sh
```

Avant cette commande, quittez l’application Ollama éventuellement ouverte dans
la zone de notification Windows. Le serveur doit être lancé par Ubuntu afin
que le diagnostic confirme un runtime entièrement WSL.

Le script est idempotent et réalise les opérations suivantes :

1. refuse WSL1, une mauvaise version d’Ubuntu ou un dépôt sous `/mnt` ;
2. installe les outils Ubuntu nécessaires ;
3. configure le dépôt APT officiel de ROS 2 ;
4. installe ROS 2 Humble Desktop, Nav2, Gazebo et TurtleBot3 ;
5. initialise `rosdep` ;
6. crée `.venv` avec `--system-site-packages` pour rendre `rclpy` accessible ;
7. installe les dépendances NLP, Jupyter et les tests ;
8. construit le package ROS 2 avec `colcon` ;
9. exécute les tests Python ;
10. installe Ollama dans WSL, démarre son service et télécharge `llama3.2:1b`.

Le script demande le mot de passe Linux pour `sudo`. L’installation ROS, PyTorch et Ollama peut prendre du temps et télécharger plusieurs gigaoctets.

Pour installer ROS/Python sans Ollama :

```bash
bash scripts/wsl_setup.sh --skip-ollama
```

## 6. Préparer le checkpoint DistilBERT

Le checkpoint final n’est pas sur GitHub, car ses poids dépassent la limite d’un dépôt Git classique.

### Option A — copier le modèle déjà présent sur Windows

La copie est une migration unique. Les exécutions suivantes restent entièrement dans WSL :

```bash
cd ~/projects/NLP-Robot-Commander
mkdir -p models
cp -a \
  /mnt/c/Users/DELL/Documents/NLP/models/distilbert-robot-commander-3intents \
  models/
```

Vérifiez les fichiers indispensables :

```bash
test -f models/distilbert-robot-commander-3intents/config.json
test -f models/distilbert-robot-commander-3intents/model.safetensors
```

### Option B — réentraîner dans WSL

```bash
source .venv/bin/activate
python scripts/train_intent_classifier.py \
  --output-dir models/distilbert-robot-commander-3intents \
  --artifacts-dir artifacts/training_3intents \
  --epochs 12 \
  --batch-size 8 \
  --seed 42
```

Le premier entraînement télécharge le modèle Hugging Face de base. Sur CPU, il peut être long.

## 7. Diagnostiquer l’installation

Exécutez :

```bash
bash scripts/wsl_check.sh
```

Le diagnostic vérifie notamment :

- WSL2 et Ubuntu 22.04 ;
- stockage du dépôt côté Linux ;
- ROS 2 Humble et les packages Nav2/TurtleBot3 ;
- `.venv`, `rclpy`, PyTorch et Transformers ;
- build `colcon` du projet ;
- checkpoint DistilBERT ;
- serveur et modèle Ollama ;
- affichage WSLg pour Gazebo/RViz2.

Corrigez toutes les lignes `[ERREUR]` avant de continuer. Un avertissement sur DistilBERT ou Ollama signifie que la démonstration complète n’est pas encore prête.

## 8. Lancer les tests et reconstruire

Après une modification du code :

```bash
bash scripts/wsl_build.sh
```

Ce script exécute `rosdep`, `colcon`, les tests et la compilation Python. Le résultat de référence actuel est :

```text
56 tests réussis
```

Dans VS Code, la commande équivalente est **Terminal > Run Task > WSL: build package and test**.

## 9. Lancer la démonstration NLP + LLM + mémoire

Vérifiez Ollama :

```bash
ollama list
curl http://127.0.0.1:11434/api/tags
```

Si le service ne répond pas :

```bash
ollama serve
```

Gardez ce terminal ouvert, puis lancez dans un autre terminal :

```bash
cd ~/projects/NLP-Robot-Commander
bash scripts/wsl_run_demo.sh --clear-memory
```

Essayez successivement :

```text
va cuisine
refais la dernière commande
t'es où ?
va dans le salon
arrête-toi immédiatement
```

Points attendus :

- `va cuisine` donne `navigate` vers `cuisine` ;
- `refais...` donne `source: memory_rules` et `memory_used: true` ;
- `t'es où ?` donne `report` avec les règles déterministes ;
- l’arrêt explicite donne `source: safety_rules` ;
- le LLM ne peut jamais envoyer directement une commande ROS 2.

Tapez `quit` pour quitter.

## 10. Ouvrir le notebook de présentation

Dans VS Code WSL, ouvrez :

```text
NLP_Robot_Commander_Presentation.ipynb
```

Cliquez sur **Select Kernel**, puis choisissez :

```text
.venv/bin/python
```

Cliquez sur **Run All**. Les résultats principaux sont déjà enregistrés dans le notebook, ce qui permet aussi de le présenter sans refaire l’entraînement.

Pour activer la cellule Ollama, remplacez `RUN_LLM = False` par `RUN_LLM = True`.

## 11. Lancer Gazebo, Nav2 et le nœud NLP

### Terminal 1 — Ollama

Seulement si le service systemd n’est pas actif :

```bash
ollama serve
```

### Terminal 2 — simulation complète

Avec la carte TurtleBot3 par défaut :

```bash
cd ~/projects/NLP-Robot-Commander
bash scripts/wsl_run_simulation.sh
```

Avec votre propre carte :

```bash
bash scripts/wsl_run_simulation.sh /chemin/absolu/vers/map.yaml
```

Le script :

- charge ROS 2, `.venv` et le workspace ;
- vérifie le checkpoint, WSLg et Ollama ;
- définit `TURTLEBOT3_MODEL=burger` ;
- démarre Gazebo, Nav2 et `nlp_commander` ;
- synchronise le spawn Gazebo et la pose initiale AMCL à `(-2.0, -0.5, 0.0)` ;
- active Ollama avec un délai initial de 60 secondes.

Attendez le message `Localisation confirmée` dans le terminal. Sur la carte
TurtleBot3 par défaut, il n'est plus nécessaire de cliquer sur **2D Pose
Estimate**. Avec une carte ou un spawn personnalisé, utilisez par exemple :

```bash
INITIAL_X=1.0 INITIAL_Y=-0.5 INITIAL_YAW=1.57 \
  bash scripts/wsl_run_simulation.sh /chemin/absolu/vers/map.yaml
```

Vous pouvez aussi lancer avec `AUTO_INITIAL_POSE=false` et définir la pose à la
main dans RViz2.

### Terminal 3 — client de commandes

```bash
cd ~/projects/NLP-Robot-Commander
source scripts/wsl_env.sh
ros2 run nlp_robot_commander terminal_client
```

Le client affiche directement les événements JSON publiés par le Commander.

### Terminal 4 — statuts observables

```bash
cd ~/projects/NLP-Robot-Commander
source scripts/wsl_env.sh
ros2 topic echo /nlp_commander/status
```

Vérifiez également le serveur Nav2 :

```bash
ros2 action info /navigate_to_pose
```

## 12. Recalibrer les waypoints

Les coordonnées de `src/nlp_robot_commander/config/waypoints.yaml` sont déjà
placées dans des zones libres de la carte TurtleBot3 par défaut. Pour une autre
carte, calibrez chaque pièce :

1. choisissez une pose libre dans RViz2 ;
2. relevez `x`, `y` et `yaw` dans le frame `map` ;
3. modifiez le fichier YAML ;
4. reconstruisez avec `bash scripts/wsl_build.sh` ;
5. relancez la simulation ;
6. testez d’abord la pose avec **Nav2 Goal**, puis avec une phrase.

## 13. Commandes VS Code disponibles

Ouvrez **Terminal > Run Task** :

| Tâche | Usage |
|---|---|
| `WSL: setup full stack` | installation initiale complète |
| `WSL: check full environment` | diagnostic reproductible |
| `WSL: build package and test` | rebuild ROS + 56 tests |
| `WSL: run all tests` | tests Python uniquement |
| `WSL: run NLP demo` | démo terminal NLP/LLM/mémoire |
| `WSL: run simulation` | Gazebo + Nav2 + nœud NLP |

Dans **Run and Debug**, les configurations `WSL: NLP demo...` utilisent automatiquement `.venv/bin/python`.

## 14. Dépannage

| Symptôme | Correction |
|---|---|
| VS Code affiche PowerShell | Fermez la fenêtre et exécutez `code .` depuis Ubuntu. |
| Le dépôt est sous `/mnt/c` | Clonez-le dans `~/projects`; ne déplacez pas `.venv`. |
| `rclpy` est introuvable | Recréez `.venv` avec `--system-site-packages` via `wsl_setup.sh`. |
| `ollama serve` indique que le port est utilisé | Ollama fonctionne déjà; vérifiez avec `curl .../api/tags`. |
| Ollama ne démarre pas comme service | Activez systemd ou gardez `ollama serve` dans un terminal. |
| Checkpoint introuvable | Copiez le dossier depuis Windows ou réentraînez-le dans WSL. |
| Gazebo/RViz2 ne s’ouvre pas | Exécutez `wsl --update`, `wsl --shutdown`, puis vérifiez `$WAYLAND_DISPLAY`. |
| Gazebo est très lent | Mettez à jour le pilote graphique Windows; utilisez Ubuntu natif pour la soutenance si nécessaire. |
| `action_server_unavailable` | Attendez l’activation de Nav2 et vérifiez `/navigate_to_pose`. |
| `localization_unavailable` | Attendez `Localisation confirmée`; sinon vérifiez `/initialpose` et `map -> base_link`. |
| `navigation_feedback` sans déplacement | Vérifiez `/cmd_vel`, les roues Gazebo et le temps simulé avec les commandes ci-dessous. |
| `navigation_finished` avec `aborted` | Le but est inaccessible ou dans un obstacle; testez-le avec **Nav2 Goal** puis recalibrez-le. |
| `position_unavailable` | Vérifiez `ros2 run tf2_ros tf2_echo map base_link`. |

Diagnostic rapide dans un terminal sourcé :

```bash
ros2 run tf2_ros tf2_echo map base_link
ros2 action info /navigate_to_pose
ros2 topic info /cmd_vel -v
ros2 topic hz /clock
```

## 15. Mise à jour quotidienne

Dans WSL :

```bash
cd ~/projects/NLP-Robot-Commander
git pull
bash scripts/wsl_build.sh
bash scripts/wsl_check.sh
```

Pour préparer la soutenance, poursuivez avec [`checklist_demo.md`](checklist_demo.md) et [`ACTIONS_MANUELLES.md`](ACTIONS_MANUELLES.md).
