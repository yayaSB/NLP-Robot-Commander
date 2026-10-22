# Audit initial du dépôt

Date de l’audit : 22 octobre 2026.

## État observé avant correction

- Le projet exposait quatre classes alors que le périmètre final en exige trois.
- Les anciens corpus, checkpoints, graphiques, rapports et diapositives partageaient encore cette taxonomie obsolète.
- Les 14 tests initiaux passaient, mais ils vérifiaient seulement le traitement NLP élémentaire.
- L’annulation Nav2 était annoncée comme réussie immédiatement après la demande, sans attendre le résultat de l’action.
- Un `Twist` nul était envoyé systématiquement et pouvait donner une fausse impression de confirmation.
- Le repli lexical était activé par défaut et masquait un modèle absent ou corrompu.
- Les négations, destinations multiples, commandes séquentielles, caractères de contrôle et longueurs excessives n’étaient pas contrôlés.
- La position TF était rapportée sans vérifier l’âge de la transformation.
- Le chemin du modèle était relatif, donc dépendant du répertoire de lancement.
- Les métriques existantes provenaient de l’ancienne taxonomie et ne pouvaient pas être conservées.

## Tests de référence avant modification

Commande exécutée : `python -m pytest`.

Résultat : **14 tests réussis**. Ce résultat est une référence historique, pas une validation ROS 2.

## Décisions de correction

1. Taxonomie figée à `navigate`, `stop`, `report` dans les données, le modèle, le pipeline et ROS 2.
2. Corpus reconstruit avec des splits explicites et un test indépendant.
3. Garde-fous déterministes appliqués avant toute action robotique.
4. Action Nav2 utilisée directement afin de suivre acceptation, annulation et résultat.
5. Repli lexical désactivé par défaut.
6. Métriques entièrement régénérées ; aucun chiffre historique n’est réutilisé.
7. Validation Gazebo/Nav2 déclarée manuelle tant qu’elle n’a pas été exécutée sur Ubuntu 22.04.
