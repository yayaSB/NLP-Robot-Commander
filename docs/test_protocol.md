# Protocole de la campagne de 50 tests

## Préparation

1. Entraîner une seule version du modèle et noter son hash Git.
2. Ne pas intégrer les 50 phrases au jeu d'entraînement.
3. Démarrer Gazebo, AMCL, Nav2 et `nlp_commander` avec la même carte.
4. Vérifier séparément que chaque waypoint est atteignable.
5. Ajouter les obstacles seulement pour les cas `obstacle_nav`.

## Exécution

Pour chaque ligne de `dataset/test_commands.csv` :

1. Publier exactement le texte indiqué.
2. Relever `predicted_intent`, `confidence` et l'entité dans le statut.
3. Pour `navigate`, attendre le résultat Nav2 et remplir `nav_result`.
4. Pour `stop`, vérifier l'annulation et la publication d'une vitesse nulle.
5. Pour `report`, comparer la pose annoncée à TF/RViz2.
6. Ajouter une observation courte dans `notes` sans modifier l'attendu.

## Catégories d'échec

| Code | Critère |
|---|---|
| `WRONG_INTENT` | L'intention prédite diffère de l'intention attendue. |
| `WRONG_OR_MISSING_PARAMETER` | L'intention est correcte, mais la destination ou l'objet est absent/erroné. |
| `NAVIGATION_FAILURE` | Intention et destination correctes, mais Nav2 échoue ou la cible est inaccessible. |

Une destination volontairement inconnue est un succès de sécurité lorsque le système prédit `navigate` mais refuse d'envoyer un but.

## Métriques à rapporter

- Accuracy globale sur 50 phrases.
- Précision, rappel et F1 par intention, plus moyennes macro.
- Exactitude d'extraction sur les commandes `navigate` et `pick`.
- Taux de succès Nav2 sur les destinations valides.
- Nombre de refus sûrs pour les destinations inconnues.
- Distribution des trois modes d'échec.

La matrice de confusion et le CSV brut doivent être conservés sous `artifacts/test_campaign/` avec le hash du commit et la date d'exécution.

