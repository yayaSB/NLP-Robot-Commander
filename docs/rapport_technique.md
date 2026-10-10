# Rapport technique — NLP Robot Commander

> Résultats NLP mesurés le 10 octobre 2026. Les résultats Nav2 restent à compléter sous Ubuntu 22.04/Gazebo.

## Résumé

Ce projet réalise une interface en français pour commander un robot TurtleBot3 simulé. Un DistilBERT multilingue fine-tuné reconnaît quatre intentions. Un extracteur d'entités fournit les paramètres, puis un nœud ROS 2 dialogue avec Nav2, TF et les topics applicatifs. La robustesse est évaluée sur 50 phrases inédites et les erreurs sont séparées en classification, extraction et navigation.

## 1. Objectifs et périmètre

Le système doit : reconnaître `navigate`, `stop`, `pick` et `report`; extraire une destination ou un objet; agir dans Gazebo; refuser les ordres dangereux ou incomplets; et produire des métriques reproductibles. La préhension physique est représentée par une requête ROS 2 lorsque le robot ne possède pas de bras.

## 2. Données

Le jeu d'apprentissage contient 80 phrases équilibrées, soit 20 exemples par intention. Le split est stratifié à 80/20 avec la graine 42. La campagne finale contient 50 formulations inédites couvrant phrases longues, ellipses, synonymes, ponctuation, ambiguïtés, multi-intentions, destinations inconnues et obstacles.

Cette taille est adaptée à un prototype pédagogique, mais insuffisante pour conclure à une généralisation large. Le jeu de validation de 16 phrases sert au choix du checkpoint; les 50 commandes restent séparées jusqu'au test final.

## 3. Modèle NLP

Le checkpoint de départ est `distilbert-base-multilingual-cased`. La tête de classification possède quatre sorties. Les hyperparamètres retenus après comparaison sont : 20 époques, batch de 8, learning rate de 2×10⁻⁵, weight decay de 0,01 et longueur maximale de 128 tokens. Le meilleur checkpoint est choisi selon le F1 macro de validation.

L'extraction des destinations utilise un dictionnaire d'alias normalisés. Cette solution déterministe est interprétable et adaptée au faible nombre de pièces. Les objets sont extraits à partir de patrons verbaux; une approche NER serait préférable pour un vocabulaire ouvert.

## 4. Intégration ROS 2

Le package `nlp_robot_commander` est un package `ament_python`. Le nœud reçoit le texte sur `/nlp_command`. `navigate` produit une pose dans le repère `map` et appelle Nav2. `stop` annule la tâche et publie un `Twist` nul. `pick` publie une requête structurée. `report` lit la transformation `map → base_link`.

Les garde-fous sont un seuil de confiance, la liste fermée des waypoints et l'absence d'action en cas de paramètre manquant. Tous les choix sont publiés sous forme de statuts JSON pour l'audit.

## 5. Protocole expérimental

L'entraînement et l'évaluation sont exécutés depuis un commit identifié. Les métriques comprennent accuracy, précision, rappel, F1 et matrice de confusion. Pour chaque navigation, le résultat Nav2 est relevé. Les erreurs sont classées en mauvaise intention, mauvais paramètre ou navigation inaccessible.

## 6. Résultats

| Mesure | Validation (16) | Test inédit (50) |
|---|---:|---:|
| Accuracy | 93,75 % | 78,00 % |
| Précision macro | 95,00 % | 76,37 % |
| Rappel macro | 93,75 % | 77,63 % |
| F1 macro | 93,65 % | 76,56 % |

**Exactitude d'extraction :** 100 % (25/25), conditionnellement à une intention `navigate` ou `pick` correctement classée.  
**Taux de succès Nav2 :** À MESURER.  
**Refus sûrs de destinations inconnues :** À MESURER.

Les figures et résultats bruts sont générés dans `artifacts/training_20ep/` et `artifacts/test_campaign_20ep/`. Sur le test inédit, `pick` obtient le meilleur F1 (88,00 %), tandis que `stop` reste le plus difficile (63,16 %). Onze commandes sur cinquante ont une mauvaise intention; aucune erreur d'entité supplémentaire n'est observée lorsque l'intention est correcte.

## 7. Analyse des échecs

Le catalogue généré contient 11 erreurs d'intention et aucune erreur de paramètre conditionnelle à une intention correcte. Les formulations elliptiques (« Cuisine, maintenant », « STOP ! STOP ! », « Position actuelle ») et le vocabulaire hors distribution (« pose dans le repère map ») dominent les erreurs. Quatre prédictions pourtant correctes restent sous le seuil de confiance de 0,65 et sont donc refusées en exécution; ce choix réduit les actions incertaines mais diminue le taux de commandes exécutées. Les échecs Nav2 devront être ajoutés après simulation et ne doivent pas être confondus avec la performance du classifieur.

## 8. Limites et améliorations

- Augmenter et diversifier le corpus, puis utiliser une validation croisée ou plusieurs graines.
- Ajouter des exemples négatifs et une intention `unknown`.
- Remplacer les règles objet par un NER entraîné lorsque le vocabulaire grandit.
- Gérer explicitement les commandes composées avec un planificateur d'actions.
- Remplacer la reconnaissance Google optionnelle par `faster-whisper` local pour mesurer le bruit audio.
- Tester sur robot réel et intégrer une confirmation vocale pour les ordres critiques.

## Conclusion

Le prototype fournit une chaîne complète, modulaire et auditable reliant compréhension du langage et navigation autonome. La conclusion finale devra confirmer ou infirmer l'objectif de performance à partir des fichiers de métriques réellement produits.

