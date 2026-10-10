# Catalogue des modes d'échec mesurés

Nombre de commandes analysées : **50**  
Nombre d'échecs : **13**

## WRONG_INTENT (13)

Mauvaise intention prédite par le classifieur.

| ID | Commande | Attendu | Prédit | Entité prédite | Notes |
|---|---|---|---|---|---|
| T005 | Cuisine, maintenant | navigate | report |  |  |
| T007 | Au bureau, s'il te plaît | navigate | pick |  |  |
| T008 | Retour base | navigate | stop |  |  |
| T009 | Va dans la CUISINE ! | navigate | report |  |  |
| T018 | STOP ! STOP ! | stop | report |  |  |
| T020 | Peux-tu annuler le trajet vers la cuisine ? | stop | navigate | cuisine |  |
| T022 | Reste exactement à cet endroit | stop | report |  |  |
| T024 | Halte au mouvement du robot | stop | navigate |  |  |
| T025 | Freine et garde ta position | stop | report |  |  |
| T038 | Position actuelle | report | stop |  |  |
| T041 | Donne ta pose dans le repère map | report | pick |  |  |
| T043 | Rapport de localisation demandé | report | stop |  |  |
| T046 | Localisation du robot, s'il te plaît | report | pick |  |  |

## WRONG_OR_MISSING_PARAMETER (0)

Intention correcte mais entité absente ou erronée.

Aucun cas observé.

## NAVIGATION_FAILURE (0)

Commande correcte mais objectif refusé ou inaccessible par Nav2.

Aucun cas observé.
