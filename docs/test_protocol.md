# Protocole de test reproductible

## 1. Tests statiques et unitaires

```bash
python -m pytest
python -m compileall -q scripts src tests
```

Couverture fonctionnelle : normalisation, corpus, extraction, décisions, routage par mocks, chargement invalide du modèle et machine d’état d’annulation.

## 2. Audit des données

```bash
python scripts/audit_dataset.py --output artifacts/dataset_audit.json
```

Le script vérifie les trois labels, l’équilibre, les doublons normalisés, les recouvrements exacts et les quasi-doublons inter-splits avec un seuil de similarité de 0,94.

## 3. Entraînement

```bash
python scripts/train_intent_classifier.py \
  --output-dir models/distilbert-robot-commander-3intents \
  --artifacts-dir artifacts/training_3intents \
  --epochs 12 --batch-size 8 --seed 42
```

Le meilleur checkpoint est sélectionné sur le F1 macro de validation. Les états d’optimiseur ne sont pas sauvegardés afin de limiter l’espace disque.

## 4. Test indépendant

```bash
python scripts/evaluate_intent_classifier.py \
  --model models/distilbert-robot-commander-3intents \
  --output-dir artifacts/test_campaign_3intents
```

Mesures : accuracy, précision/rappel/F1 par classe, F1 macro, matrice de confusion, confiance, entité extraite et acceptation finale.

## 5. Sûreté

```bash
python scripts/evaluate_safety_commands.py \
  --model models/distilbert-robot-commander-3intents \
  --output-dir artifacts/safety_campaign_transformers
```

Les cas incluent commande vide, négation, arrêt nié, destination inconnue, destinations multiples, séquence, action hors périmètre, texte hors domaine et caractère de contrôle.

## 6. ROS 2 / Gazebo

Exécuter la checklist de démonstration et enregistrer les événements JSON. Les critères minimaux sont : but Nav2 accepté, arrivée ou échec explicite, annulation réellement confirmée, arrêt sans but actif, TF fraîche, TF absente/périmée et refus sans émission de but.

Cette dernière section n’a pas été exécutée sur la machine Windows d’audit.
