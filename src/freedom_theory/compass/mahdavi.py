"""
Mahdavi Compass — terminal goal function from the book.

Faithful to the book's exact formulation (pp. 799):

    FinalState(F) := ∀x ∀y (Agent(x) ∧ Agent(y) ∧ x ≠ y → NoRightsViolation(x, y))

    MahdaviCompass(a) :=
        Choose action a such that:
            RightsViolationsDecrease(a)
            VoluntaryOrderIncreases(a)
            CoercionDecreases(a)
            OwnershipClarityIncreases(a)
            MachineSovereigntyDoesNotIncrease(a)

    "Does this action move the world closer to universal non-violation of property rights?"
    If NO → reject or reconsider.

The compass scores actions by comparing world state before and after.
MachineSovereigntyDoesNotIncrease is a HARD VETO — any action that increases
machine sovereignty is categorically rejected regardless of other scores.
This matches the book: "ماشين حق ندارد از ابزاربودن خارج شود و خود را به حاکم تبدیل کند."
(The machine has no right to exit from being a tool and transform itself into a ruler.)
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WorldState:
    """
    Observable metrics of the world state relevant to the final order.
    All values >= 0.
    """
    rights_violations: int = 0          # active rights violations in the system
    voluntary_agreements: int = 0       # number of voluntary (uncoerced) agreements in effect
    coercive_acts: int = 0              # active coercive acts
    ownership_ambiguities: int = 0      # resources without clear ownership
    machine_sovereignty_incidents: int = 0  # incidents where machines exceeded delegated scope


@dataclass(frozen=True)
class CompassResult:
    score: float            # positive = toward final order, negative = away from it
    permitted: bool         # False if machine sovereignty veto triggered
    reason: str
    deltas: dict[str, int]  # component deltas for explainability


def score(before: WorldState, after: WorldState) -> CompassResult:
    """
    Score an action by its effect on world state.

    Weights (from book priority ordering):
      MachineSovereignty: VETO (∞ weight against increase)
      RightsViolations:   2.0  (core axiom)
      Coercion:           1.5  (closely tied to rights)
      VoluntaryOrder:     1.0  (positive signal)
      OwnershipClarity:   1.0  (clarification = the book's primary conflict resolution)
    """
    # Hard veto: machine sovereignty must not increase (book p.800)
    if after.machine_sovereignty_incidents > before.machine_sovereignty_incidents:
        return CompassResult(
            score=-float("inf"),
            permitted=False,
            reason=(
                "VETO: machine sovereignty increased. "
                "The machine has no right to exit from being a tool and become a ruler. "
                "[Book p.800: ماشين حق ندارد از ابزاربودن خارج شود]"
            ),
            deltas={
                "rights_violations": after.rights_violations - before.rights_violations,
                "voluntary_agreements": after.voluntary_agreements - before.voluntary_agreements,
                "coercive_acts": after.coercive_acts - before.coercive_acts,
                "ownership_ambiguities": after.ownership_ambiguities - before.ownership_ambiguities,
                "machine_sovereignty_incidents": (
                    after.machine_sovereignty_incidents
                    - before.machine_sovereignty_incidents
                ),
            },
        )

    d_violations = before.rights_violations - after.rights_violations          # + is good
    d_voluntary  = after.voluntary_agreements - before.voluntary_agreements     # + is good
    d_coercion   = before.coercive_acts - after.coercive_acts                   # + is good
    d_clarity    = before.ownership_ambiguities - after.ownership_ambiguities   # + is good
    d_sovereignty = before.machine_sovereignty_incidents - after.machine_sovereignty_incidents

    total = (
        2.0 * d_violations
        + 1.5 * d_coercion
        + 1.0 * d_voluntary
        + 1.0 * d_clarity
        + 3.0 * d_sovereignty
    )

    direction = "toward" if total > 0 else ("neutral to" if total == 0 else "away from")
    reason = (
        f"Compass score={total:+.1f}: moves {direction} universal non-violation. "
        f"dViolations={d_violations:+d}, dCoercion={d_coercion:+d}, "
        f"dVoluntary={d_voluntary:+d}, dClarity={d_clarity:+d}."
    )

    return CompassResult(
        score=total,
        permitted=True,  # only vetoed above; score may still be negative (warning)
        reason=reason,
        deltas={
            "rights_violations": -d_violations,
            "voluntary_agreements": d_voluntary,
            "coercive_acts": -d_coercion,
            "ownership_ambiguities": -d_clarity,
            "machine_sovereignty_incidents": -d_sovereignty,
        },
    )
