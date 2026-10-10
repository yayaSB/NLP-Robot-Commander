# Catalogue des modes d'échec — référentiel

Ce document définit la taxonomie. Le catalogue **mesuré** sera généré après l'évaluation par `scripts/analyze_failure_modes.py`.

## F1 — Mauvaise intention prédite

**Exemple :** « Va chercher la boîte rouge » est classé `navigate` au lieu de `pick`.  
**Cause probable :** chevauchement lexical ou données insuffisantes.  
**Détection :** comparaison `predicted_intent` / `expected_intent`.  
**Réponse :** enrichir les paraphrases ambiguës, conserver un seuil de confiance et analyser la matrice de confusion.

## F2 — Paramètre absent ou erroné

**Exemple :** `navigate` est correct, mais « salle de travail » n'est pas associé à `bureau`.  
**Cause probable :** alias absent ou règle d'extraction trop stricte.  
**Détection :** comparaison de l'entité canonique attendue et prédite.  
**Réponse :** enrichir les alias, normaliser accents/casse, refuser tout waypoint inconnu.

## F3 — Destination inaccessible par Nav2

**Exemple :** la cuisine est correctement comprise, mais un obstacle ferme le couloir.  
**Cause probable :** planification impossible, localisation incertaine ou timeout.  
**Détection :** résultat Nav2 `FAILED`/`CANCELED` et journaux du costmap.  
**Réponse :** distinguer cet échec du NLP, conserver l'arrêt possible et informer l'utilisateur.

## Cas contrôlés qui ne sont pas des pannes

- Faible confiance : commande refusée avant action.
- Destination inconnue : intention reconnue, mais aucun but Nav2 envoyé.
- `pick` sans manipulateur : requête correctement publiée, fonctionnalité physique hors périmètre.

