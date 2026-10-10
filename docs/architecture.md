# Architecture technique

## Chaîne de traitement

1. Le client terminal ou micro publie une chaîne UTF-8 sur `/nlp_command`.
2. DistilBERT produit une intention et une distribution de probabilités.
3. Le seuil de confiance rejette une prédiction incertaine.
4. L'extracteur cherche une destination connue ou un objet.
5. Le nœud exécute l'adaptateur correspondant et publie un événement JSON sur `/nlp_commander/status`.

| Intention | Validation | Sortie ROS 2 |
|---|---|---|
| `navigate` | Destination présente dans les waypoints | `BasicNavigator.goToPose()` |
| `stop` | Aucune entité requise | `cancelTask()` et `Twist()` nul |
| `pick` | Objet extrait | `/nlp_commander/pick_request` |
| `report` | Transformation TF disponible | Position `map → base_link` dans le statut |

## Contrats des topics

- `/nlp_command` (`std_msgs/String`) : phrase originale.
- `/nlp_commander/status` (`std_msgs/String`) : objet JSON avec `event` et détails.
- `/nlp_commander/pick_request` (`std_msgs/String`) : objet JSON contenant l'objet et la phrase source.
- `/cmd_vel` (`geometry_msgs/Twist`) : vitesse nulle lors d'un arrêt.

## Événements de statut

`command_parsed`, `navigation_started`, `navigation_finished`, `navigation_cancelled`, `pick_requested`, `position_report` et `position_failed`. La décision `command_parsed` inclut toujours l'intention, la confiance, les entités et un éventuel `error_code`.

## Séparation des responsabilités

- `intent_classifier.py` : prédiction Transformer ou secours lexical.
- `entity_extractor.py` : alias de destination et objet.
- `command_processor.py` : validation sûre, sans dépendance ROS.
- `nlp_commander_node.py` : transport ROS, TF et appels Nav2.

Cette séparation permet de tester le NLP sans Gazebo et d'attribuer correctement un échec à la classification, à l'extraction ou à la navigation.

