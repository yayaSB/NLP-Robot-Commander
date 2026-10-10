# Comparaison des expériences DistilBERT

Même base (`distilbert-base-multilingual-cased`), même split stratifié, même graine 42, batch 8 et learning rate 2e-5.

| Expérience | Accuracy validation | F1 macro validation | Accuracy test (50) | F1 macro test (50) |
|---|---:|---:|---:|---:|
| 12 époques | 81,25 % | 77,22 % | 74,00 % | 71,69 % |
| **20 époques** | **93,75 %** | **93,65 %** | **78,00 %** | **76,56 %** |

Le modèle 20 époques est retenu. Le gain de validation est important, mais le gain plus faible sur le test inédit indique encore un écart de généralisation. L'objectif supérieur à 90 % est atteint sur validation, pas sur la campagne indépendante.

