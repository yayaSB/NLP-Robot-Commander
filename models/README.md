# Checkpoint sélectionné

Le checkpoint local sélectionné est `models/distilbert-robot-commander-20ep/`.

- Base : `distilbert-base-multilingual-cased`
- Graine : 42
- Époques : 20
- Batch : 8
- Learning rate : 2e-5
- Validation : accuracy 93,75 %, F1 macro 93,65 % (16 exemples)
- Test inédit : accuracy 78,00 %, F1 macro 76,56 % (50 exemples)

Les poids sont volontairement ignorés par Git en raison de leur taille. Ils se recréent avec la commande d'entraînement du `README.md`. Pour les partager, utilisez Git LFS ou une release GitHub et conservez `config.json`, les fichiers du tokenizer et `model.safetensors` ensemble.
