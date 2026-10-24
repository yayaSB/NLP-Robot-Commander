from nlp_robot_commander.command_memory import CommandMemory
from nlp_robot_commander.types import CommandDecision


def test_memory_persists_only_recent_accepted_commands(tmp_path):
    path = tmp_path / "commands.sqlite3"
    memory = CommandMemory(path, max_entries=2)
    memory.record("refus", CommandDecision(False, "unknown", 0.0))
    for destination in ("cuisine", "salon", "bureau"):
        memory.record(
            f"Va dans le {destination}",
            CommandDecision(
                True,
                "navigate",
                0.9,
                destination=destination,
                source="llm",
            ),
        )
    memory.close()

    reopened = CommandMemory(path, max_entries=2)
    records = reopened.recent(10)

    assert [item.destination for item in records] == ["salon", "bureau"]
    assert all(item.source == "llm" for item in records)
    reopened.close()


def test_memory_can_be_cleared(tmp_path):
    memory = CommandMemory(tmp_path / "commands.sqlite3")
    memory.record("Stop", CommandDecision(True, "stop", 1.0))

    memory.clear()

    assert memory.recent() == []
    memory.close()
