# Trame de soutenance

## Structure recommandée

1. Besoin : commander un robot mobile en français sans action ambiguë.
2. Périmètre : trois intentions et quatre waypoints d’exemple.
3. Données : 162 phrases de développement et 45 phrases de test indépendantes.
4. Modèle : DistilBERT multilingue, graine 42, meilleur F1 macro.
5. Sûreté : refus avant routage et priorité de l’arrêt explicite.
6. ROS 2 : ActionClient Nav2, machine d’état d’annulation et TF fraîche.
7. Résultats : 97,22 % validation, 100 % test indépendant, 15/15 sûreté.
8. Limites : petit corpus, poids non versionnés, validation Gazebo manuelle.
9. Démonstration guidée par `checklist_demo.md`.

## Formulation correcte des résultats

Dire : « Sur les 45 phrases du test indépendant fourni, les trois classes sont correctement reconnues. »

Ne pas dire : « Le système comprend toutes les formulations » ou « la navigation est validée » avant la campagne Ubuntu/Gazebo.

## Questions probables

- Pourquoi DistilBERT ? Pour adapter un encodeur multilingue préentraîné à un petit corpus tout en restant plus léger que BERT complet.
- Pourquoi des règles en plus du modèle ? Elles imposent des invariants de sûreté vérifiables avant toute action physique.
- Pourquoi un test distinct ? Pour éviter d’annoncer la performance mesurée sur les données utilisées pour sélectionner le modèle.
- Quand l’arrêt est-il confirmé ? Après un résultat Nav2 `canceled`, ou immédiatement si aucun but n’était actif.
