from dataclasses import dataclass
from enum import Enum


class NavigationPhase(str, Enum):
    IDLE = "idle"
    GOAL_PENDING = "goal_pending"
    ACTIVE = "active"
    CANCEL_PENDING = "cancel_pending"
    CANCEL_UNCONFIRMED = "cancel_unconfirmed"


class StopState(str, Enum):
    CONFIRMED = "confirmed"
    PENDING = "pending"
    UNCONFIRMED = "unconfirmed"


@dataclass(frozen=True)
class StopOutcome:
    state: StopState
    reason: str


class NavigationStateMachine:
    """État testable qui interdit d'assimiler une demande à un arrêt confirmé."""

    def __init__(self) -> None:
        self.phase = NavigationPhase.IDLE
        self.destination: str | None = None
        self.stop_requested = False

    def request_goal(self, destination: str) -> None:
        if self.phase != NavigationPhase.IDLE:
            raise RuntimeError(f"Navigation déjà occupée: {self.phase.value}")
        self.phase = NavigationPhase.GOAL_PENDING
        self.destination = destination
        self.stop_requested = False

    def goal_response(self, accepted: bool) -> bool:
        """Retourne True si le but accepté doit être annulé immédiatement."""
        if self.phase != NavigationPhase.GOAL_PENDING:
            raise RuntimeError("Réponse de but reçue dans un état incohérent.")
        if not accepted:
            self.reset()
            return False
        if self.stop_requested:
            self.phase = NavigationPhase.CANCEL_PENDING
            return True
        self.phase = NavigationPhase.ACTIVE
        return False

    def request_stop(self) -> StopOutcome:
        if self.phase == NavigationPhase.IDLE:
            return StopOutcome(StopState.CONFIRMED, "no_active_goal")
        self.stop_requested = True
        if self.phase == NavigationPhase.GOAL_PENDING:
            return StopOutcome(StopState.PENDING, "goal_response_pending")
        self.phase = NavigationPhase.CANCEL_PENDING
        return StopOutcome(StopState.PENDING, "cancellation_required")

    def cancellation_response(self, accepted: bool) -> StopOutcome:
        if self.phase != NavigationPhase.CANCEL_PENDING:
            raise RuntimeError("Réponse d'annulation reçue dans un état incohérent.")
        if accepted:
            return StopOutcome(StopState.PENDING, "awaiting_canceled_result")
        self.phase = NavigationPhase.CANCEL_UNCONFIRMED
        return StopOutcome(StopState.UNCONFIRMED, "cancellation_rejected")

    def cancellation_timeout(self) -> StopOutcome:
        if self.phase != NavigationPhase.CANCEL_PENDING:
            raise RuntimeError("Délai d'annulation reçu dans un état incohérent.")
        self.phase = NavigationPhase.CANCEL_UNCONFIRMED
        return StopOutcome(StopState.UNCONFIRMED, "cancellation_timeout")

    def complete(self, result: str) -> StopOutcome | None:
        was_stop_requested = self.stop_requested
        self.reset()
        if not was_stop_requested:
            return None
        if result == "canceled":
            return StopOutcome(StopState.CONFIRMED, "goal_canceled")
        return StopOutcome(StopState.UNCONFIRMED, f"goal_finished_{result}")

    def reset(self) -> None:
        self.phase = NavigationPhase.IDLE
        self.destination = None
        self.stop_requested = False
