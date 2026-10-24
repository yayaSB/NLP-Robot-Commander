#!/usr/bin/env python3
"""Démo locale du pipeline, sans installation de ROS 2."""

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1] / "src" / "nlp_robot_commander"
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from nlp_robot_commander.command_memory import CommandMemory
from nlp_robot_commander.command_processor import CommandProcessor
from nlp_robot_commander.entity_extractor import EntityExtractor
from nlp_robot_commander.intent_classifier import (
    RuleBasedIntentClassifier,
    TransformersIntentClassifier,
)
from nlp_robot_commander.llm_interpreter import OllamaLlmInterpreter


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path)
    parser.add_argument(
        "--waypoints",
        type=Path,
        default=Path("src/nlp_robot_commander/config/waypoints.yaml"),
    )
    parser.add_argument("--threshold", type=float, default=0.65)
    parser.add_argument("--ambiguity-margin", type=float, default=0.10)
    parser.add_argument("--llm", action="store_true", help="Active le LLM local Ollama")
    parser.add_argument("--llm-model", default="llama3.2:1b")
    parser.add_argument("--ollama-endpoint", default="http://127.0.0.1:11434")
    parser.add_argument("--llm-timeout", type=float, default=20.0)
    parser.add_argument("--no-llm-fallback", action="store_true")
    parser.add_argument(
        "--memory-db",
        type=Path,
        default=Path.home()
        / ".local"
        / "share"
        / "nlp_robot_commander"
        / "command_memory.sqlite3",
    )
    parser.add_argument("--clear-memory", action="store_true")
    args = parser.parse_args()
    classifier = (
        TransformersIntentClassifier(args.model)
        if args.model
        else RuleBasedIntentClassifier()
    )
    extractor = EntityExtractor.from_yaml(args.waypoints)
    memory = CommandMemory(args.memory_db) if args.llm else None
    if memory is not None and args.clear_memory:
        memory.clear()
    llm = (
        OllamaLlmInterpreter(
            tuple(extractor.waypoints),
            model=args.llm_model,
            endpoint=args.ollama_endpoint,
            timeout_sec=args.llm_timeout,
        )
        if args.llm
        else None
    )
    processor = CommandProcessor(
        classifier,
        extractor,
        args.threshold,
        args.ambiguity_margin,
        llm_interpreter=llm,
        memory=memory,
        allow_llm_fallback=not args.no_llm_fallback,
    )
    mode = "DistilBERT" if args.model else "classifieur lexical de secours"
    if args.llm:
        mode = f"LLM local {args.llm_model} avec mémoire + {mode} en secours"
    print(f"Mode: {mode}")
    if memory is not None:
        print(f"Mémoire locale: {args.memory_db}")
    print("Saisissez `quit` pour quitter.")
    try:
        while True:
            try:
                text = input("> ").strip()
            except EOFError:
                break
            if text.casefold() in {"quit", "exit", "q"}:
                break
            decision = processor.process(text)
            print(json.dumps(asdict(decision), ensure_ascii=False, indent=2))
            processor.remember(text, decision)
    finally:
        if memory is not None:
            memory.close()


if __name__ == "__main__":
    main()
