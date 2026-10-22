from typing import Protocol

from .types import CommandDecision


class RobotActions(Protocol):
    def navigate(self, destination: str) -> None: ...

    def stop(self) -> None: ...

    def report(self) -> None: ...


class CommandRouter:
    """Route uniquement les décisions déjà acceptées vers l'adaptateur robot."""

    def __init__(self, actions: RobotActions) -> None:
        self.actions = actions

    def route(self, decision: CommandDecision) -> bool:
        if not decision.accepted:
            return False
        if decision.intent == "navigate":
            if not decision.destination:
                raise ValueError("Une navigation acceptée doit avoir une destination.")
            self.actions.navigate(decision.destination)
        elif decision.intent == "stop":
            self.actions.stop()
        elif decision.intent == "report":
            self.actions.report()
        else:
            raise ValueError(f"Intention non routable: {decision.intent}")
        return True
