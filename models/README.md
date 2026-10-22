# Checkpoint local

Le checkpoint attendu est `models/distilbert-robot-commander-3intents/`.

- Base : `distilbert-base-multilingual-cased`
- Labels : `navigate`, `stop`, `report`
- Graine : 42
- Époques maximales : 12
- Batch : 8
- Learning rate : 2e-5
- Validation mesurée : accuracy 97,22 %, F1 macro 97,22 % sur 36 phrases
- Test indépendant mesuré : accuracy et F1 macro 100 % sur 45 phrases

Les poids sont ignorés par Git à cause de leur taille. Recréez-les avec la commande du README principal. Conservez ensemble `config.json`, les fichiers du tokenizer et `model.safetensors`.
