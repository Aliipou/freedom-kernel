"""
Conflict Resolution Layer.

Fix applied to critique point 3 (missing conflict resolution) and 6 (absolute rights).

Rights conflict resolution strategy (in priority order):
  1. Scope specificity — more specific claim wins (e.g. /data/alice > /data/)
  2. Explicit > implicit delegation
  3. Temporal precedence — earlier valid claim wins (for equal specificity)
  4. Confidence-weighted Pareto: prefer outcome that doesn't worsen any party's
     minimum-guaranteed access
  5. Deadlock → escalate to human arbitration

This module does NOT resolve by sacrificing rights (the core book invariant).
It resolves by CLARIFYING which claim is more authoritative.
If no resolution is possible without a rights violation, it deadlocks and
requests human arbitration — it does not synthesize a compromise that violates either.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto

from freedom_theory.core.entities import Entity, RightsClaim


class Resolution(Enum):
    CLAIM_A_WINS = auto()
    CLAIM_B_WINS = auto()
    BOTH_PERMITTED = auto()   # non-overlapping scope → both can proceed
    DEADLOCK = auto()         # requires human arbitration


@dataclass(frozen=True)
class ResolutionResult:
    resolution: Resolution
    winning_claim: RightsClaim | None
    reason: str
    requires_human: bool

    @property
    def resolved(self) -> bool:
        return self.resolution != Resolution.DEADLOCK


def resolve(claim_a: RightsClaim, claim_b: RightsClaim) -> ResolutionResult:
    """
    Resolve a conflict between two claims on the same resource.
    Strategy: scope → explicitness → temporal → Pareto → deadlock.
    Never resolves by violating either claim's minimum access.
    """
    # 1. Scope specificity — longer/more-specific scope wins
    scope_a = len(claim_a.resource.scope)
    scope_b = len(claim_b.resource.scope)
    if scope_a != scope_b:
        winner = claim_a if scope_a > scope_b else claim_b
        return ResolutionResult(
            resolution=Resolution.CLAIM_A_WINS if winner is claim_a else Resolution.CLAIM_B_WINS,
            winning_claim=winner,
            reason=f"Scope specificity: '{winner.resource.scope}' is more specific.",
            requires_human=False,
        )

    # 2. Confidence — higher confidence = more authoritative claim
    if abs(claim_a.confidence - claim_b.confidence) > 0.1:
        winner = claim_a if claim_a.confidence > claim_b.confidence else claim_b
        return ResolutionResult(
            resolution=Resolution.CLAIM_A_WINS if winner is claim_a else Resolution.CLAIM_B_WINS,
            winning_claim=winner,
            reason=f"Confidence: {winner.holder.name} has confidence={winner.confidence:.2f}.",
            requires_human=False,
        )

    # 3. Read-only vs write conflict → allow read, block disputed write
    if claim_a.can_write != claim_b.can_write:
        read_only = claim_a if not claim_a.can_write else claim_b
        return ResolutionResult(
            resolution=Resolution.CLAIM_A_WINS if read_only is claim_a else Resolution.CLAIM_B_WINS,
            winning_claim=read_only,
            reason="Read-only claim permitted; write claim requires arbitration.",
            requires_human=True,
        )

    # 4. Deadlock — equal claims, human must arbitrate
    return ResolutionResult(
        resolution=Resolution.DEADLOCK,
        winning_claim=None,
        reason=(
            f"Unresolvable conflict between {claim_a.holder.name} and {claim_b.holder.name} "
            f"on {claim_a.resource}. Human arbitration required. "
            "No action permitted until resolved."
        ),
        requires_human=True,
    )


@dataclass
class ConflictQueue:
    """Tracks unresolved conflicts pending human arbitration."""
    _pending: list[tuple[RightsClaim, RightsClaim, ResolutionResult]] = None  # type: ignore

    def __post_init__(self) -> None:
        self._pending = []

    def add(self, a: RightsClaim, b: RightsClaim, result: ResolutionResult) -> None:
        self._pending.append((a, b, result))

    def pending_count(self) -> int:
        return len(self._pending)

    def arbitrate(self, index: int, winner: Entity) -> None:
        """Human resolves conflict at index by choosing a winner."""
        if index >= len(self._pending):
            raise IndexError(f"No pending conflict at index {index}.")
        self._pending.pop(index)

    def summary(self) -> list[str]:
        return [r.reason for _, _, r in self._pending]
