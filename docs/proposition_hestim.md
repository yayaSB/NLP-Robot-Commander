# Fiche de proposition — NLP Robot Commander

**Établissement :** HESTIM  
**Durée :** 6 semaines  
**Technologies :** Ubuntu 22.04, ROS 2 Humble, Nav2, Gazebo, Python, PyTorch, Hugging Face Transformers

## Contexte et problématique

Le pilotage d'un robot mobile impose habituellement une interface graphique ou des commandes techniques. Le projet propose une interface en français permettant à un utilisateur de donner des ordres naturels. Le défi consiste à transformer une phrase potentiellement variable ou ambiguë en une action robotique structurée et sûre.

## Objectif

Réaliser et évaluer un pipeline complet capable de reconnaître quatre intentions — navigation, arrêt, préhension et rapport de position — puis d'exécuter l'action correspondante dans une simulation TurtleBot3/Nav2. Le système doit refuser les commandes insuffisamment fiables et documenter ses modes d'échec.

## Méthode

Un jeu équilibré de 80 phrases françaises sert au fine-tuning de DistilBERT multilingue. Un extracteur déterministe associe les noms de pièces aux coordonnées de la carte et extrait les objets. Le nœud ROS 2 transmet les destinations à `NavigateToPose`, annule une tâche pour `stop`, publie une requête pour `pick` et lit TF pour `report`. Une campagne distincte de 50 phrases mesure accuracy, précision, rappel, F1, extraction des paramètres et comportement Nav2.

## Résultats attendus

- Un classifieur visant une accuracy supérieure à 90 %, valeur à confirmer expérimentalement.
- Un démonstrateur texte → intention/paramètre → action dans Gazebo.
- Une matrice de confusion et un catalogue des erreurs NLP, paramètres et navigation.
- Un dépôt reproductible avec tests, documentation, rapport et vidéo de démonstration.

## Planning synthétique

| Semaine | Résultat principal |
|---|---|
| 1 | Simulation, waypoints et dataset |
| 2–3 | Fine-tuning, extraction et évaluation initiale |
| 3–4 | Nœud ROS 2 et intégration Nav2 |
| 4–5 | Campagne de 50 tests et analyse des échecs |
| 6 | Rapport, vidéo, dépôt et soutenance |

## Risques et réponses

Le petit dataset peut produire une variance élevée : split stratifié, graine fixe et test indépendant sont conservés. Une destination inconnue ou une faible confiance entraîne un refus. Les obstacles dynamiques sont distingués des erreurs NLP. La préhension reste une interface simulée si aucun bras robotique n'est disponible.

