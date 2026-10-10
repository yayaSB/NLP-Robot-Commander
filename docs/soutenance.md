# Plan de soutenance et vidéo

## Démonstration vidéo (3 à 5 minutes)

1. Afficher Gazebo et RViz2 avec le robot localisé.
2. Montrer une navigation vers la cuisine depuis le terminal.
3. Envoyer `stop` pendant le trajet et montrer l'annulation.
4. Relancer une navigation, puis demander un rapport de position.
5. Envoyer une destination inconnue et montrer le refus sans mouvement.
6. Montrer une requête `pick` sur le topic dédié.
7. Terminer par la matrice de confusion et un exemple de mode d'échec.

Enregistrez simultanément le terminal des statuts pour rendre visible la chaîne texte → intention → entité → action.

## Présentation (10 à 12 diapositives)

1. Problème et objectif.
2. Périmètre et quatre intentions.
3. Architecture globale.
4. Dataset et stratégie de séparation.
5. Fine-tuning DistilBERT.
6. Extraction des paramètres.
7. Intégration ROS 2/Nav2.
8. Protocole des 50 tests.
9. Métriques et matrice de confusion.
10. Catalogue des pannes.
11. Démonstration.
12. Limites, améliorations et conclusion.

## Checklist finale

- Remplacer tous les champs `À MESURER` du rapport.
- Vérifier les coordonnées de chaque waypoint sur la carte finale.
- Noter le hash Git du modèle testé.
- Tester une fois la vidéo et le dépôt sur une machine propre.
- Ne pas annoncer de préhension physique si seul le topic de requête est utilisé.
