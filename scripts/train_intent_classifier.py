#!/usr/bin/env python3
"""Fine-tuning reproductible de DistilBERT pour les trois intentions."""

import argparse
import inspect
import json
import platform
import random
import re
import unicodedata
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import torch
from datasets import Dataset
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    Trainer,
    TrainingArguments,
)

LABELS = ["navigate", "stop", "report"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=Path("dataset/dataset.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("models/distilbert-robot-commander"))
    parser.add_argument("--artifacts-dir", type=Path, default=Path("artifacts/training"))
    parser.add_argument("--model-name", default="distilbert-base-multilingual-cased")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--local-files-only", action="store_true")
    return parser.parse_args()


def validate_dataset(frame: pd.DataFrame) -> None:
    required = {"text", "intent", "split"}
    if not required.issubset(frame.columns):
        raise ValueError(f"Colonnes requises: {sorted(required)}")
    unknown = set(frame["intent"]) - set(LABELS)
    if unknown:
        raise ValueError(f"Intentions inconnues: {sorted(unknown)}")
    if frame["text"].isna().any() or not frame["text"].astype(str).str.strip().all():
        raise ValueError("Le dataset contient une phrase vide.")
    if set(frame["split"]) != {"train", "validation"}:
        raise ValueError("La colonne split doit contenir train et validation.")
    for split_name, subset in frame.groupby("split"):
        counts = subset["intent"].value_counts()
        if set(counts.index) != set(LABELS) or counts.min() < 2:
            raise ValueError(f"Split non équilibré ou incomplet: {split_name}")

    normalized = frame["text"].map(normalize_for_audit)
    duplicates = frame[normalized.duplicated(keep=False)]
    if not duplicates.empty:
        raise ValueError("Phrases dupliquées après normalisation.")
    train_texts = set(normalized[frame["split"] == "train"])
    validation_texts = set(normalized[frame["split"] == "validation"])
    if train_texts & validation_texts:
        raise ValueError("Fuite exacte entre entraînement et validation.")


def normalize_for_audit(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", str(text).casefold())
    ascii_text = "".join(
        char for char in decomposed if not unicodedata.combining(char)
    )
    return re.sub(r"\W+", " ", ascii_text).strip()


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def build_training_arguments(args: argparse.Namespace) -> TrainingArguments:
    kwargs = {
        "output_dir": str(args.output_dir / "checkpoints"),
        "learning_rate": args.learning_rate,
        "per_device_train_batch_size": args.batch_size,
        "per_device_eval_batch_size": args.batch_size,
        "num_train_epochs": args.epochs,
        "weight_decay": 0.01,
        # save_only_model évite les états d'optimiseur très volumineux tout en
        # permettant de restaurer le meilleur checkpoint de validation.
        "save_strategy": "epoch",
        "logging_strategy": "epoch",
        "save_only_model": True,
        "load_best_model_at_end": True,
        "metric_for_best_model": "f1_macro",
        "greater_is_better": True,
        "save_total_limit": 2,
        "seed": args.seed,
        "data_seed": args.seed,
        "report_to": "none",
    }
    # Compatibilité Transformers 4.41+ (renommage de evaluation_strategy).
    parameters = inspect.signature(TrainingArguments.__init__).parameters
    strategy_key = "eval_strategy" if "eval_strategy" in parameters else "evaluation_strategy"
    kwargs[strategy_key] = "epoch"
    return TrainingArguments(**kwargs)


def main() -> None:
    args = parse_args()
    set_seed(args.seed)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.artifacts_dir.mkdir(parents=True, exist_ok=True)

    frame = pd.read_csv(args.dataset)
    validate_dataset(frame)
    label2id = {label: index for index, label in enumerate(LABELS)}
    id2label = {index: label for label, index in label2id.items()}
    frame["label"] = frame["intent"].map(label2id)
    train_frame = frame[frame["split"] == "train"].copy()
    validation_frame = frame[frame["split"] == "validation"].copy()
    train_frame.to_csv(args.artifacts_dir / "train_split.csv", index=False)
    validation_frame.to_csv(args.artifacts_dir / "validation_split.csv", index=False)

    # DistilBERT utilise BertPreTokenizer, pas le regex Mistral. Le drapeau False
    # évite qu'une version récente de Transformers tente un correctif incompatible.
    tokenizer = AutoTokenizer.from_pretrained(
        args.model_name,
        local_files_only=args.local_files_only,
        fix_mistral_regex=False,
    )

    def tokenize(batch):
        return tokenizer(batch["text"], truncation=True, max_length=128)

    train_dataset = Dataset.from_pandas(train_frame[["text", "label"]], preserve_index=False)
    validation_dataset = Dataset.from_pandas(
        validation_frame[["text", "label"]], preserve_index=False
    )
    train_dataset = train_dataset.map(tokenize, batched=True)
    validation_dataset = validation_dataset.map(tokenize, batched=True)

    model = AutoModelForSequenceClassification.from_pretrained(
        args.model_name,
        num_labels=len(LABELS),
        id2label=id2label,
        label2id=label2id,
        local_files_only=args.local_files_only,
    )

    def compute_metrics(evaluation):
        predictions = np.argmax(evaluation.predictions, axis=-1)
        report = classification_report(
            evaluation.label_ids,
            predictions,
            labels=list(range(len(LABELS))),
            target_names=LABELS,
            output_dict=True,
            zero_division=0,
        )
        return {
            "accuracy": accuracy_score(evaluation.label_ids, predictions),
            "precision_macro": report["macro avg"]["precision"],
            "recall_macro": report["macro avg"]["recall"],
            "f1_macro": report["macro avg"]["f1-score"],
        }

    trainer_kwargs = {
        "model": model,
        "args": build_training_arguments(args),
        "train_dataset": train_dataset,
        "eval_dataset": validation_dataset,
        "data_collator": DataCollatorWithPadding(tokenizer=tokenizer),
        "compute_metrics": compute_metrics,
    }
    trainer_parameters = inspect.signature(Trainer.__init__).parameters
    if "processing_class" in trainer_parameters:
        trainer_kwargs["processing_class"] = tokenizer
    else:
        trainer_kwargs["tokenizer"] = tokenizer
    trainer = Trainer(**trainer_kwargs)
    trainer.train()
    trainer.save_model(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)

    output = trainer.predict(validation_dataset)
    predicted_ids = np.argmax(output.predictions, axis=-1)
    true_ids = output.label_ids
    shifted_logits = output.predictions - np.max(output.predictions, axis=1, keepdims=True)
    probabilities = np.exp(shifted_logits) / np.exp(shifted_logits).sum(axis=1, keepdims=True)
    validation_results = validation_frame.copy()
    validation_results["predicted_intent"] = [id2label[index] for index in predicted_ids]
    validation_results["confidence"] = probabilities.max(axis=1)
    validation_results.to_csv(
        args.artifacts_dir / "validation_predictions.csv", index=False
    )
    report = classification_report(
        true_ids,
        predicted_ids,
        labels=list(range(len(LABELS))),
        target_names=LABELS,
        output_dict=True,
        zero_division=0,
    )
    accuracy = float(accuracy_score(true_ids, predicted_ids))
    metrics = {
        "accuracy": accuracy,
        "split_policy": "curated_train_validation",
        "train_size": len(train_frame),
        "validation_size": len(validation_frame),
        "seed": args.seed,
        "model_name": args.model_name,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "learning_rate": args.learning_rate,
        "environment": {
            "python": platform.python_version(),
            "torch": torch.__version__,
        },
        "classification_report": report,
    }
    (args.artifacts_dir / "validation_metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    matrix = confusion_matrix(true_ids, predicted_ids, labels=list(range(len(LABELS))))
    plt.figure(figsize=(7, 6))
    sns.heatmap(matrix, annot=True, fmt="d", cmap="Blues", xticklabels=LABELS, yticklabels=LABELS)
    plt.xlabel("Intention prédite")
    plt.ylabel("Intention réelle")
    plt.title("Matrice de confusion — validation")
    plt.tight_layout()
    plt.savefig(args.artifacts_dir / "confusion_matrix.png", dpi=180)
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

