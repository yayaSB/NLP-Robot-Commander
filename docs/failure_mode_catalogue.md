# Catalogue des modes d’échec

| Code ou événement | Couche | Détection | Réponse sûre |
|---|---|---|---|
| `EMPTY_COMMAND` | entrée | chaîne vide | aucun routage |
| `COMMAND_TOO_LONG` | entrée | plus de 240 caractères | aucun routage |
| `CONTROL_CHARACTER` | entrée | caractère de contrôle Unicode | aucun routage |
| `NEGATED_COMMAND` | langage | navigation niée | aucun but Nav2 |
| `NEGATED_STOP` | langage | arrêt explicitement nié | demande refusée comme ambiguë |
| `MULTIPLE_DESTINATIONS` | entités | plusieurs waypoints | demande de reformulation |
| `SEQUENTIAL_COMMAND` | langage | connecteur séquentiel | aucun routage |
| `UNSUPPORTED_ACTION` | périmètre | verbe d’action non autorisé | aucun routage |
| `UNKNOWN_INTENT` | NLP | aucune preuve lexicale compatible | aucun routage |
| `LOW_CONFIDENCE` | NLP | score inférieur au seuil | aucun routage |
| `AMBIGUOUS_INTENT` | NLP | écart top-1/top-2 insuffisant | aucun routage |
| `UNKNOWN_DESTINATION` | entités | aucun waypoint connu | aucun but Nav2 |
| `navigation_rejected` | ROS 2 | serveur absent ou but refusé | statut explicite |
| `stop_unconfirmed` | ROS 2 | refus, erreur, timeout ou résultat incompatible | ne jamais annoncer un arrêt réussi |
| `position_unavailable` | TF | transformation absente | aucune position inventée |
| `position_stale` | TF | âge supérieur au seuil | aucune position présentée comme actuelle |

## Résultats observés

La campagne NLP indépendante du 22 octobre 2026 ne contient aucune erreur sur 45 phrases. La campagne adversariale réussit 15 décisions sur 15. Cette absence d’erreur dans un petit échantillon n’élimine pas les risques de généralisation.

Les échecs de navigation dus à un obstacle, à la localisation, au costmap ou au lifecycle Nav2 doivent être enregistrés séparément d’une erreur NLP pendant la validation Gazebo.
