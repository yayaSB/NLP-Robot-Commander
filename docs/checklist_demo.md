# Checklist de démonstration

## Avant la séance

- [ ] WSL2/Ubuntu 22.04 et WSLg fonctionnels, ou Ubuntu 22.04 natif.
- [ ] `bash scripts/wsl_check.sh` ne signale aucune erreur.
- [ ] ROS 2 Humble, Nav2, Gazebo, TurtleBot3 et Ollama installés dans Ubuntu.
- [ ] Checkpoint local entraîné et chemin absolu connu.
- [ ] `bash scripts/wsl_build.sh` réussit avec les 56 tests.
- [ ] Audit du dataset en état `ok: true`.
- [ ] Carte chargée et waypoints recalibrés dans RViz2.
- [ ] Pose initiale du robot définie.
- [ ] `/navigate_to_pose` disponible et lifecycle Nav2 actif.
- [ ] TF `map → base_link` présente et récente.

## Scénario de soutenance

1. Montrer les trois intentions et l’architecture.
2. Lancer `ros2 topic echo /nlp_commander/status`.
3. Envoyer « Rends-toi dans la cuisine » et montrer `navigation_requested`, `navigation_started`, puis le résultat.
4. Pendant un second trajet, envoyer « Arrête-toi immédiatement » et montrer la chaîne jusqu’à `stop_confirmed`.
5. Répéter l’arrêt sans but actif et montrer `reason: no_active_goal`.
6. Envoyer « Où te trouves-tu ? » et comparer la pose à RViz2.
7. Envoyer « Ne va pas dans la cuisine » et constater qu’aucun but n’est émis.
8. Envoyer « Va dans la cuisine pas dans le salon » et montrer le refus multi-destination.
9. Envoyer « Va dans la cuisine puis dans le laboratoire » et montrer le refus séquentiel.
10. Présenter les métriques en séparant clairement NLP local et validation robotique.

## Preuves à conserver

- [ ] Vidéo avec terminal, Gazebo et RViz2 visibles.
- [ ] Copie des événements JSON.
- [ ] Capture de la pose initiale et des waypoints.
- [ ] Résultat d’un but inaccessible ou obstacle dynamique.
- [ ] Résultat d’une TF indisponible ou périmée.
- [ ] Version Git et paramètres utilisés.
