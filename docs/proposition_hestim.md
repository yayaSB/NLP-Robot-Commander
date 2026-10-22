# Proposition de projet HESTIM

## Titre

NLP Robot Commander — commande sûre d’un robot mobile par langage naturel français.

## Problématique

Transformer une phrase libre en une action Nav2 contrôlée sans envoyer de but incomplet, ambigu ou non autorisé, tout en produisant des traces permettant d’identifier la couche fautive.

## Périmètre

Le prototype reconnaît trois intentions : navigation vers un waypoint connu, arrêt d’une navigation et rapport de la pose actuelle. Le robot cible est TurtleBot3 Burger sous Ubuntu 22.04, ROS 2 Humble, Nav2, Gazebo et RViz2.

## Méthode

- Fine-tuning de DistilBERT multilingue sur un corpus français équilibré.
- Extraction déterministe de destinations autorisées.
- Politique de refus avant le routage ROS 2.
- Client d’action `NavigateToPose` avec suivi asynchrone du résultat.
- Lecture TF avec timeout et contrôle de fraîcheur.
- Évaluation séparée : validation figée, test indépendant et campagne adversariale.

## Livrables

Code source, datasets, scripts reproductibles, tests unitaires, artefacts de métriques, rapport final, guide utilisateur, protocole de test et checklist de démonstration.

## Risques

Le petit corpus peut surestimer les performances. Les waypoints doivent être recalibrés. Les comportements Nav2, TF et Gazebo ne peuvent être certifiés sans exécution sur la plateforme ROS 2 cible.
