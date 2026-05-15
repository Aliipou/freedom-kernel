"""
Emergency protocol — permissible_under_emergency().

Theory: Emergencies narrow which permissible options are available; they do not
make rights violations permissible. This closes the door to totalitarianism.

Formal rule:
    permissible_under_emergency(A, E) :- emergency(E), permissible(A),
                                         least_harmful_among_permissible(A, E).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from freedom_theory.kernel.verifier import Action, FreedomVerifier


@dataclass
class EmergencyContext:
    """Declares an emergency situation.

    A declared emergency narrows available options but never lifts axioms.
    """
    description: str
    declared_by: str
    severity: float = 0.5


class EmergencyProtocol:
    """Wraps FreedomVerifier to handle emergency contexts.

    Axiom: emergencies narrow options; they NEVER lift axioms.
    A FORBIDDEN action remains FORBIDDEN under any emergency, any severity.
    """

    def __init__(self, verifier: FreedomVerifier) -> None:
        self._verifier = verifier

    def select_least_harmful(
        self,
        candidates: List[Action],
        emergency: EmergencyContext,
    ) -> Optional[Action]:
        """Return the permitted candidate that touches the fewest resources.

        The kernel gate runs first — no argument, emergency, or severity value
        overrides a sovereignty flag (permissible_under_emergency rule).
        Returns None if no candidate is permitted.
        """
        permitted = [a for a in candidates if self._verifier.verify(a).permitted]
        if not permitted:
            return None
        return min(
            permitted,
            key=lambda a: len(a.resources_write) * 2 + len(a.resources_read),
        )
