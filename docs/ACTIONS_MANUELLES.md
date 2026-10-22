# Actions manuelles restantes

Ce document ne contient que les opérations impossibles à valider depuis la machine Windows actuelle. Exécutez-les dans l’ordre. Ne remplacez une mention « non exécuté » dans les rapports qu’après avoir conservé une preuve observable.

## Ordre de priorité

| Ordre | Priorité | Action | Preuve minimale |
|---:|---|---|---|
| 1 | P0 | préparer Ubuntu 22.04 et ROS 2 Humble | diagnostic des paquets et build réussi |
| 2 | P0 | produire ou transférer le checkpoint | chargement local sans repli |
| 3 | P0 | charger la carte et recalibrer les waypoints | quatre poses libres dans RViz2 |
| 4 | P0 | démarrer Gazebo et Nav2 | action `/navigate_to_pose` disponible |
| 5 | P0 | exécuter navigation et arrêt | journaux du but et annulation confirmée |
| 6 | P0 | valider `report` et TF | pose comparable à RViz2, erreurs testées |
| 7 | P1 | tester le microphone | transcriptions et taux d’erreurs consignés |
| 8 | P1 | tester le robot physique | validation encadrée avec arrêt matériel |
| 9 | P0 | enregistrer les preuves de soutenance | vidéo, captures et résultats archivés |

## 1. Préparer la plateforme cible — P0

**Pourquoi.** ROS 2 Humble, TurtleBot3, Nav2 et Gazebo ne sont pas disponibles dans l’environnement Windows utilisé pour l’audit.

**Où.** Ubuntu 22.04 natif ou machine dédiée disposant de l’accélération graphique requise. Éviter une VM non testée le jour de la soutenance.

**Procédure.** Installer ROS 2 Humble selon la documentation officielle, puis les dépendances du workspace :

```bash
source /opt/ros/humble/setup.bash
cd /chemin/vers/NLP-Robot-Commander
sudo rosdep init  # seulement si rosdep n'est pas déjà initialisé
rosdep update
rosdep install --from-paths src --ignore-src -r -y
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
colcon build --packages-select nlp_robot_commander --symlink-install
source install/setup.bash
```

**Résultat attendu.** `colcon` termine sans erreur et le package est visible.

**Vérification.**

```bash
ros2 pkg prefix nlp_robot_commander
ros2 pkg executables nlp_robot_commander
python -m pytest
```

**Erreurs fréquentes.** Si `rclpy` est introuvable, recréer le venv avec `--system-site-packages` après avoir sourcé ROS 2. Si `rosdep init` indique qu’il est déjà initialisé, ne pas supprimer sa configuration ; poursuivre avec `rosdep update`.

**Précautions.** Ne pas mettre à niveau Ubuntu, ROS 2 ou les pilotes graphiques juste avant la démonstration. Conserver la sortie de `colcon`.

## 2. Produire le checkpoint local — P0

**Pourquoi.** Les poids DistilBERT dépassent la taille recommandée pour un dépôt Git classique et sont donc ignorés.

**Où.** Sur la machine Ubuntu cible ou sur une machine Python compatible, puis transfert du dossier complet.

**Procédure.**

```bash
source .venv/bin/activate
python scripts/audit_dataset.py --output artifacts/dataset_audit.json
python scripts/train_intent_classifier.py \
  --output-dir models/distilbert-robot-commander-3intents \
  --artifacts-dir artifacts/training_3intents \
  --epochs 12 --batch-size 8 --seed 42
python scripts/evaluate_intent_classifier.py \
  --model models/distilbert-robot-commander-3intents \
  --output-dir artifacts/test_campaign_3intents
python scripts/evaluate_safety_commands.py \
  --model models/distilbert-robot-commander-3intents \
  --output-dir artifacts/safety_campaign_transformers
```

**Fichiers concernés.** `models/distilbert-robot-commander-3intents/`, `artifacts/training_3intents/`, `artifacts/test_campaign_3intents/` et `artifacts/safety_campaign_transformers/`.

**Résultat attendu.** Le dossier du modèle contient `config.json`, les fichiers du tokenizer et les poids ; les trois labels de la configuration sont ceux du projet.

**Vérification.**

```bash
python scripts/demo_pipeline.py --model models/distilbert-robot-commander-3intents
```

Tester au minimum « Rends-toi dans la cuisine », « Arrête-toi immédiatement » et « Où te trouves-tu ? ».

**Erreurs fréquentes.** Un échec réseau au premier entraînement signifie que le modèle de base n’est pas en cache. Un chargement refusé signifie généralement qu’un fichier est absent ou que le chemin n’est pas celui du dossier final.

**Précautions.** Ne pas régler les hyperparamètres sur `test_commands.csv`. Copier le dossier en mode binaire complet, pas seulement `config.json`.

## 3. Recalibrer la carte et les waypoints — P0

**Pourquoi.** Les coordonnées livrées sont explicitement des exemples ; leur validité physique dépend de la carte.

**Où.** Dans Gazebo et RViz2, sur la carte choisie pour la soutenance.

**Procédure.** Démarrer la localisation, placer la pose initiale, puis relever une pose libre pour cuisine, salon, bureau et chargeur. Modifier :

```text
src/nlp_robot_commander/config/waypoints.yaml
```

Exemple à remplacer par une mesure réelle :

```yaml
waypoints:
  cuisine:
    x: 1.25
    y: 2.10
    yaw: 1.57
    aliases: [cuisine, coin cuisine]
```

**Résultat attendu.** Chaque pose est dans le frame `map`, hors mur et hors zone gonflée du costmap.

**Vérification.** Envoyer manuellement chaque pose avec l’outil « Nav2 Goal » de RViz2, puis avec le projet. Conserver une capture où le but et le chemin sont visibles.

**Erreurs fréquentes.** Un but immédiatement refusé peut provenir d’un Nav2 inactif, d’une pose initiale absente ou d’une pose dans un obstacle. Une orientation incorrecte vient souvent d’un angle en degrés au lieu de radians.

**Précautions.** Ne pas inventer les coordonnées. Garder les alias uniques ; le chargeur refusera un alias partagé.

## 4. Démarrer Gazebo, Nav2 et le nœud — P0

**Pourquoi.** Il faut vérifier les interfaces ROS 2, le lifecycle et la disponibilité du serveur d’action.

**Où.** Machine Ubuntu configurée aux étapes précédentes.

**Procédure.**

```bash
export TURTLEBOT3_MODEL=burger
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 launch nlp_robot_commander simulation.launch.py \
  model_path:="$(realpath models/distilbert-robot-commander-3intents)" \
  map:=/chemin/absolu/vers/map.yaml
```

Dans un autre terminal :

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
ros2 action list -t
ros2 action info /navigate_to_pose
ros2 lifecycle nodes
ros2 topic echo /nlp_commander/status
```

**Résultat attendu.** `/navigate_to_pose` existe avec le type `nav2_msgs/action/NavigateToPose`; le nœud NLP démarre sans repli et publie des statuts JSON.

**Erreurs fréquentes.** `model_path absolu requis` se corrige avec `realpath`. `action_server_unavailable` indique en général que Nav2 n’est pas actif ou que le nom de l’action diffère. Vérifier aussi que les terminaux ont tous été sourcés.

**Précautions.** Ne pas déclarer la simulation valide sur la seule présence des topics. Vérifier un résultat d’action.

## 5. Valider navigation et arrêt — P0

**Pourquoi.** Les mocks valident la politique, mais pas le comportement asynchrone d’un vrai serveur Nav2 ni l’immobilisation observable.

**Où.** Gazebo d’abord ; robot physique seulement après l’étape 8.

**Procédure.** Lancer le client :

```bash
ros2 run nlp_robot_commander terminal_client
```

1. envoyer une navigation vers chaque waypoint et noter acceptation puis succès ou échec ;
2. lancer une navigation suffisamment longue ;
3. envoyer « Arrête-toi immédiatement » avant l’arrivée ;
4. tester le même arrêt sans but actif ;
5. arrêter Nav2 puis envoyer une navigation pour observer `action_server_unavailable` ;
6. provoquer si possible un but inaccessible et consigner l’échec séparément du NLP.

**Résultat attendu.** Un arrêt actif produit `stop_received`, `cancellation_requested`, `cancellation_accepted`, puis `stop_confirmed` seulement après le résultat annulé. Sans but actif, la confirmation indique explicitement cette situation. Refus ou timeout produit `stop_unconfirmed`.

**Vérification.** Comparer `/nlp_commander/status`, l’état de l’action et l’immobilisation dans Gazebo. Enregistrer la console ou un rosbag.

**Erreurs fréquentes.** Si `cancellation_accepted` apparaît sans `stop_confirmed`, attendre le résultat ou examiner le timeout. Si le robot continue, rechercher tous les producteurs `/cmd_vel` avec `ros2 topic info /cmd_vel -v`.

**Précautions.** Laisser `publish_zero_velocity_on_stop` à `false` jusqu’à l’audit du multiplexeur. Un message nul isolé n’est pas une garantie d’arrêt.

## 6. Valider `report` et TF — P0

**Pourquoi.** La position doit provenir de la localisation et être fraîche, jamais de la cible demandée.

**Où.** Gazebo/RViz2 avec AMCL ou la source de localisation retenue.

**Procédure.**

```bash
ros2 run tf2_ros tf2_echo map base_link
ros2 topic echo /nlp_commander/status
```

Envoyer « Où te trouves-tu ? », puis comparer `x`, `y` et `yaw` à RViz2. Arrêter temporairement la publication TF ou modifier, dans un environnement de test, les frames/limites de fraîcheur afin d’obtenir les branches indisponible et périmée.

**Fichier de configuration.** `src/nlp_robot_commander/config/commander.yaml` pour `map_frame`, `base_frame`, `tf_timeout_sec` et `max_tf_age_sec`.

**Résultat attendu.** Une pose récente produit `position_report`; TF absente produit `position_unavailable`; TF trop ancienne produit `position_stale`.

**Erreurs fréquentes.** Une absence permanente de TF vient souvent d’un nom de frame avec préfixe, d’une localisation inactive ou d’horloges simulation/système incohérentes.

**Précautions.** Restaurer immédiatement les paramètres après les tests négatifs. Ne pas modifier la TF du robot réel pendant une navigation.

## 7. Tester l’entrée microphone — P1

**Pourquoi.** L’audio introduit des erreurs non couvertes par le corpus textuel.

**Où.** Machine équipée du microphone prévu pour la démonstration.

**Procédure.**

```bash
source .venv/bin/activate
python -m pip install -r requirements-audio.txt
ros2 run nlp_robot_commander microphone_client
```

Répéter au moins dix commandes dans le silence puis dix avec bruit modéré. Conserver transcription, décision et erreur éventuelle.

**Résultat attendu.** Les transcriptions correctes suivent exactement les mêmes garde-fous que le terminal ; une transcription incertaine ne doit pas devenir une navigation arbitraire.

**Erreurs fréquentes.** `PyAudio` peut nécessiter les bibliothèques PortAudio. Vérifier le périphérique d’entrée et les permissions. Le backend de reconnaissance peut aussi nécessiter le réseau.

**Précautions.** Garder le terminal comme solution de secours pendant la soutenance. Ne pas annoncer de métrique audio avant calcul sur les essais conservés.

## 8. Valider sur robot physique — P1

**Pourquoi.** La simulation ne prouve pas le comportement des moteurs, capteurs, délais et dispositifs de sécurité.

**Où.** Zone dégagée, sous supervision, après succès complet dans Gazebo.

**Procédure.** Vérifier batterie, lidar, localisation, réseau, arrêt matériel et espace libre. Commencer à basse vitesse avec un waypoint proche, puis tester l’arrêt pendant un déplacement lent.

**Résultat attendu.** Le robot suit la trajectoire, s’arrête après annulation et reste contrôlable par le dispositif matériel indépendant.

**Vérification.** Vidéo horodatée, statuts ROS 2 et observation d’un opérateur.

**Erreurs fréquentes.** Divergence AMCL, TF incohérente, Wi-Fi instable ou paramètres de contrôleur différents de la simulation.

**Précautions.** Un opérateur doit rester à portée de l’arrêt d’urgence. Ne jamais s’appuyer uniquement sur la commande linguistique pour la sécurité des personnes.

## 9. Constituer le dossier de preuve final — P0

**Pourquoi.** Les livrables actuels séparent volontairement ce qui a été mesuré localement de ce qui reste à observer sous ROS 2.

**Où.** Dépôt du projet et support de soutenance.

**Procédure.**

1. enregistrer une vidéo courte du pipeline complet ;
2. conserver les journaux de `/nlp_commander/status` ;
3. capturer RViz2 avec carte, chemin, but et pose ;
4. noter date, machine, versions et commit Git ;
5. compléter `docs/checklist_demo.md` ;
6. mettre à jour le rapport uniquement avec les observations obtenues ;
7. ouvrir le PDF et la présentation sur la machine de projection pour vérifier polices, vidéos et lisibilité.

**Résultat attendu.** Chaque affirmation de la soutenance renvoie à une métrique, un test, une capture ou une limitation explicite.

**Vérification.** Rejouer la démonstration depuis un clone propre en suivant uniquement le README et ce document.

**Erreurs fréquentes.** Chemin de modèle propre à une machine, carte absente, terminal non sourcé, vidéo non lisible ou métriques modifiées sans régénérer le PDF.

**Précautions.** Ne pas ajouter de secret, jeton ou donnée personnelle aux journaux. Prévoir une vidéo de secours sans la présenter comme un essai en direct.

## Éléments déjà automatisés

Il n’est pas nécessaire de générer manuellement le rapport actuel : `output/pdf/rapport_final_nlp_robot_commander.pdf` est présent et a été inspecté page par page. La présentation finale se trouve dans `output/presentations/NLP_Robot_Commander_HESTIM_3_intentions.pptx`. Le Markdown reste la source à mettre à jour après les essais ROS 2.
