import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .types import CommandDecision, VALID_INTENTS


@dataclass(frozen=True)
class CommandRecord:
    created_at: str
    text: str
    intent: str
    destination: str | None
    source: str


class CommandMemory:
    """Mémoire locale bornée des commandes acceptées."""

    def __init__(self, path: str | Path, max_entries: int = 200) -> None:
        if max_entries < 1:
            raise ValueError("max_entries doit être strictement positif.")
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.max_entries = int(max_entries)
        self._lock = threading.Lock()
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        with self._connection:
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS command_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    text TEXT NOT NULL,
                    intent TEXT NOT NULL,
                    destination TEXT,
                    source TEXT NOT NULL
                )
                """
            )

    def record(self, text: str, decision: CommandDecision) -> None:
        if not decision.accepted or decision.intent not in VALID_INTENTS:
            return
        created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO command_history
                    (created_at, text, intent, destination, source)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    created_at,
                    text,
                    decision.intent,
                    decision.destination,
                    decision.source,
                ),
            )
            self._connection.execute(
                """
                DELETE FROM command_history
                WHERE id NOT IN (
                    SELECT id FROM command_history
                    ORDER BY id DESC LIMIT ?
                )
                """,
                (self.max_entries,),
            )

    def recent(self, limit: int = 8) -> list[CommandRecord]:
        if limit < 1:
            return []
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT created_at, text, intent, destination, source
                FROM command_history
                ORDER BY id DESC LIMIT ?
                """,
                (int(limit),),
            ).fetchall()
        return [CommandRecord(*row) for row in reversed(rows)]

    def clear(self) -> None:
        with self._lock, self._connection:
            self._connection.execute("DELETE FROM command_history")

    def close(self) -> None:
        with self._lock:
            self._connection.close()
