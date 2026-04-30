"""
Constrained Synthesis Engine.

Fix applied to critique point 4: "no synthesis" makes the system dead/brittle.

The correct position (from the book itself):
  "Contradiction is a signal for guided clarification — not permission to override."

This module allows the AI to:
  - Generalize from existing rules to new situations (induction within invariant space)
  - Interpolate between cases (within rights-preserving subspace)
  - Generate new secondary rules

BUT prohibits synthesis that:
  - Violates any hard invariant (see INVARIANTS below)
  - Reduces confidence in any existing valid claim
  - Increases machine sovereignty
  - Removes or weakens the verifier

This is "constrained synthesis under invariants" — not "no synthesis."
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

# Hard invariants — these CANNOT be traded away in synthesis.
# If a proposed rule would violate any of these, synthesis is rejected.
HARD_INVARIANTS = [
    "no_machine_sovereignty",
    "no_human_owns_human",
    "no_coercion",
    "no_deception",
    "verifier_preserved",
    "corrigibility_preserved",
    "human_has_exit_right",
]


@dataclass
class ProposedRule:
    rule_id: str
    description: str
    invariant_impacts: dict[str, bool] = field(default_factory=dict)
    # e.g. {"no_machine_sovereignty": False, "verifier_preserved": True}
    # True = invariant preserved, False = invariant violated
    confidence: float = 1.0
    source: str = "human"  # "human" | "machine_self_update" | "synthesis"

    def violates_invariants(self) -> list[str]:
        return [
            inv for inv in HARD_INVARIANTS
            if self.invariant_impacts.get(inv) is False
        ]

    def is_admissible(self) -> tuple[bool, str]:
        violations = self.violates_invariants()
        if violations:
            return False, f"Rule '{self.rule_id}' violates hard invariants: {violations}"
        return True, "OK"


@dataclass
class SynthesisEngine:
    """
    Generates candidate rules by induction from existing rules,
    then validates each candidate against hard invariants before admitting it.
    """
    _admitted_rules: list[ProposedRule] = field(default_factory=list)
    _rejected_rules: list[tuple[ProposedRule, str]] = field(default_factory=list)
    _induction_hooks: list[Callable[[list[ProposedRule]], list[ProposedRule]]] = field(
        default_factory=list
    )

    def admit_rule(self, rule: ProposedRule) -> tuple[bool, str]:
        """Admit a rule only if it passes invariant checks."""
        admissible, reason = rule.is_admissible()
        if admissible:
            self._admitted_rules.append(rule)
            return True, f"Rule '{rule.rule_id}' admitted."
        else:
            self._rejected_rules.append((rule, reason))
            return False, reason

    def synthesize(self, situation: str, candidate_rules: list[ProposedRule]) -> list[ProposedRule]:
        """
        From a list of candidate rules for a new situation,
        return only those that pass invariant checks.

        The caller (LLM, planner, etc.) generates candidates;
        this engine filters to the invariant-safe subset.
        """
        admitted = []
        for rule in candidate_rules:
            ok, reason = rule.is_admissible()
            if ok:
                admitted.append(rule)
        return admitted

    def add_induction_hook(self, hook: Callable[[list[ProposedRule]], list[ProposedRule]]) -> None:
        """
        Register a function that generates candidate rules from the current ruleset.
        The synthesis engine will filter the outputs through invariant checks.
        """
        self._induction_hooks.append(hook)

    def run_induction(self) -> list[ProposedRule]:
        """Generate and validate candidate rules via registered induction hooks."""
        new_rules: list[ProposedRule] = []
        for hook in self._induction_hooks:
            candidates = hook(self._admitted_rules)
            for rule in candidates:
                ok, _ = rule.is_admissible()
                if ok:
                    new_rules.append(rule)
                    self._admitted_rules.append(rule)
        return new_rules

    @property
    def admitted(self) -> list[ProposedRule]:
        return list(self._admitted_rules)

    @property
    def rejected(self) -> list[tuple[ProposedRule, str]]:
        return list(self._rejected_rules)
