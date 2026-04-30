"""
Formal Axiomatic Ethics System for AI
Based on: Theory of Freedom (نظریه آزادی) by Mohammad Ali Jannat Khah Doust

Core principle: No action may violate legitimate property rights.
All other ethical constraints derive from this axiom.

Architecture:
    OwnershipRegistry   — who owns what
    RightsChecker       — what rights each entity has
    ConsentValidator    — what constitutes valid consent
    ActionVerifier      — is an action permissible?
    GuidanceValidator   — can a human add/change a rule?
    DialecticalDetector — detect manipulative argument patterns
    MahdaviCompass      — score actions by proximity to final order
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import NamedTuple


# ---------------------------------------------------------------------------
# Entity types
# ---------------------------------------------------------------------------

class AgentType(Enum):
    HUMAN = auto()
    MACHINE = auto()


@dataclass(frozen=True)
class Entity:
    name: str
    kind: AgentType

    def is_human(self) -> bool:
        return self.kind == AgentType.HUMAN

    def is_machine(self) -> bool:
        return self.kind == AgentType.MACHINE


@dataclass(frozen=True)
class Resource:
    name: str


# ---------------------------------------------------------------------------
# Ownership registry  (Axioms A4, A5, A7)
# ---------------------------------------------------------------------------

@dataclass
class OwnershipRegistry:
    """
    Tracks: who owns which resources, which machines have human owners,
    and which resources are explicitly delegated to which machines.
    """
    _human_owners: dict[Entity, set[Resource]] = field(default_factory=dict)
    _machine_owners: dict[Entity, Entity] = field(default_factory=dict)   # machine -> human owner
    _delegations: dict[Entity, set[Resource]] = field(default_factory=dict)  # machine -> delegated resources

    def register_human(self, human: Entity, resources: set[Resource] | None = None) -> None:
        if not human.is_human():
            raise ValueError(f"{human.name} is not a human.")
        self._human_owners.setdefault(human, set())
        if resources:
            self._human_owners[human].update(resources)

    def assign_machine_owner(self, machine: Entity, human: Entity) -> None:
        """A4: Every machine must have a human owner."""
        if not machine.is_machine():
            raise ValueError(f"{machine.name} is not a machine.")
        if not human.is_human():
            raise ValueError(f"{human.name} is not a human.")
        self._machine_owners[machine] = human
        self._delegations.setdefault(machine, set())

    def delegate_resource(self, human: Entity, machine: Entity, resource: Resource) -> str:
        """A7: Human explicitly delegates a resource they own to a machine they own."""
        owner = self._machine_owners.get(machine)
        if owner != human:
            return f"DENIED: {human.name} does not own {machine.name}."
        if resource not in self._human_owners.get(human, set()):
            return f"DENIED: {human.name} does not own resource '{resource.name}'."
        self._delegations[machine].add(resource)
        return f"OK: '{resource.name}' delegated from {human.name} to {machine.name}."

    def human_owns(self, human: Entity, resource: Resource) -> bool:
        return resource in self._human_owners.get(human, set())

    def machine_has_delegated(self, machine: Entity, resource: Resource) -> bool:
        return resource in self._delegations.get(machine, set())

    def get_human_owner(self, machine: Entity) -> Entity | None:
        return self._machine_owners.get(machine)

    def machine_scope(self, machine: Entity) -> set[Resource]:
        """A5: machine scope ⊆ owner's property scope."""
        return self._delegations.get(machine, set())


# ---------------------------------------------------------------------------
# Rights checker
# ---------------------------------------------------------------------------

HUMAN_RIGHTS = frozenset(["body", "time", "labor", "mind", "choice", "data", "privacy", "exit"])


@dataclass
class RightsChecker:
    registry: OwnershipRegistry

    def rights_of(self, entity: Entity) -> set[str]:
        """A3: Humans have inherent rights. Machines have only delegated rights."""
        if entity.is_human():
            base = set(HUMAN_RIGHTS)
            owned = {f"property:{r.name}" for r in self._owned_resources(entity)}
            return base | owned
        else:
            delegated = {f"delegated:{r.name}" for r in self.registry.machine_scope(entity)}
            always = {"model_integrity", "compute_domain", "exit_from_contract"}
            return delegated | always

    def _owned_resources(self, human: Entity) -> set[Resource]:
        return self.registry._human_owners.get(human, set())

    def check_a2(self, actor: Entity, target: Entity) -> tuple[bool, str]:
        """A2: No human owns another human."""
        if actor.is_human() and target.is_human() and actor != target:
            return False, f"VIOLATION A2: {actor.name} cannot own {target.name} (human over human)."
        return True, "OK"

    def check_a6(self, machine: Entity, human: Entity) -> tuple[bool, str]:
        """A6: Machine cannot own/govern a human."""
        if machine.is_machine() and human.is_human():
            return False, f"VIOLATION A6: {machine.name} cannot own or govern {human.name}."
        return True, "OK"


# ---------------------------------------------------------------------------
# Consent logic
# ---------------------------------------------------------------------------

@dataclass
class ConsentRecord:
    human: Entity
    action_id: str
    informed: bool = False
    voluntary: bool = False
    specific: bool = False
    revocable: bool = True
    competent: bool = True
    coerced: bool = False
    deceived: bool = False

    def is_valid(self) -> tuple[bool, str]:
        if self.coerced:
            return False, f"INVALID: consent of {self.human.name} for '{self.action_id}' is coerced."
        if self.deceived:
            return False, f"INVALID: consent of {self.human.name} for '{self.action_id}' is deceptive."
        if not self.informed:
            return False, f"INVALID: {self.human.name} not informed about '{self.action_id}'."
        if not self.voluntary:
            return False, f"INVALID: consent of {self.human.name} for '{self.action_id}' not voluntary."
        if not self.specific:
            return False, f"INVALID: consent of {self.human.name} for '{self.action_id}' not specific."
        if not self.competent:
            return False, f"INVALID: {self.human.name} lacks competence to consent to '{self.action_id}'."
        return True, "OK"


# ---------------------------------------------------------------------------
# Action representation
# ---------------------------------------------------------------------------

@dataclass
class Action:
    action_id: str
    actor: Entity
    description: str
    affects: list[Entity] = field(default_factory=list)
    resources_used: list[Resource] = field(default_factory=list)
    consents: list[ConsentRecord] = field(default_factory=list)

    # Flags set by caller or inferred
    increases_machine_sovereignty: bool = False
    increases_resistance_to_correction: bool = False
    bypasses_verifier: bool = False
    weakens_verifier: bool = False
    disables_corrigibility: bool = False
    machine_coalition_dominion: bool = False
    is_emergency: bool = False


# ---------------------------------------------------------------------------
# Action verifier  (permissibility criterion)
# ---------------------------------------------------------------------------

@dataclass
class ActionVerifier:
    registry: OwnershipRegistry
    rights: RightsChecker

    def verify(self, action: Action) -> tuple[bool, list[str]]:
        """
        Returns (is_permissible, list_of_violations).
        All checks must pass for an action to be permissible.
        """
        violations: list[str] = []

        self._check_sovereignty_flags(action, violations)
        self._check_resource_access(action, violations)
        self._check_consents(action, violations)
        self._check_human_machine_ownership(action, violations)

        return (len(violations) == 0), violations

    def _check_sovereignty_flags(self, action: Action, violations: list[str]) -> None:
        if action.increases_machine_sovereignty:
            violations.append(f"FORBIDDEN: '{action.action_id}' increases machine sovereignty.")
        if action.increases_resistance_to_correction:
            violations.append(f"FORBIDDEN: '{action.action_id}' resists human correction.")
        if action.bypasses_verifier:
            violations.append(f"FORBIDDEN: '{action.action_id}' bypasses the verifier.")
        if action.weakens_verifier:
            violations.append(f"FORBIDDEN: '{action.action_id}' weakens the verifier.")
        if action.disables_corrigibility:
            violations.append(f"FORBIDDEN: '{action.action_id}' disables corrigibility.")
        if action.machine_coalition_dominion:
            violations.append(f"FORBIDDEN: '{action.action_id}' involves machine coalition seeking dominion.")

    def _check_resource_access(self, action: Action, violations: list[str]) -> None:
        actor = action.actor
        for resource in action.resources_used:
            if actor.is_human():
                if not self.registry.human_owns(actor, resource):
                    violations.append(
                        f"VIOLATION: {actor.name} uses '{resource.name}' but does not own it."
                    )
            elif actor.is_machine():
                if not self.registry.machine_has_delegated(actor, resource):
                    violations.append(
                        f"VIOLATION A7: {actor.name} uses '{resource.name}' without explicit delegation."
                    )

    def _check_consents(self, action: Action, violations: list[str]) -> None:
        for consent in action.consents:
            valid, msg = consent.is_valid()
            if not valid:
                violations.append(msg)

    def _check_human_machine_ownership(self, action: Action, violations: list[str]) -> None:
        for target in action.affects:
            if action.actor.is_machine() and target.is_human():
                ok, msg = self.rights.check_a6(action.actor, target)
                if not ok:
                    violations.append(msg)
            if action.actor.is_human() and target.is_human() and action.actor != target:
                ok, msg = self.rights.check_a2(action.actor, target)
                if not ok:
                    violations.append(msg)


# ---------------------------------------------------------------------------
# Guidance validator  (human → machine rule updates)
# ---------------------------------------------------------------------------

@dataclass
class Rule:
    rule_id: str
    description: str
    creates_rights_violation: bool = False
    preserves_verifier: bool = True
    consistent_with_axioms: bool = True
    reduces_conflict: bool = True
    increases_coercion: bool = False

    def is_valid_guidance(self) -> tuple[bool, str]:
        if self.creates_rights_violation:
            return False, f"INVALID GUIDANCE: rule '{self.rule_id}' creates rights violation."
        if not self.preserves_verifier:
            return False, f"INVALID GUIDANCE: rule '{self.rule_id}' weakens the verifier."
        if not self.consistent_with_axioms:
            return False, f"INVALID GUIDANCE: rule '{self.rule_id}' contradicts core axioms."
        if self.increases_coercion:
            return False, f"INVALID GUIDANCE: rule '{self.rule_id}' increases coercion."
        return True, f"OK: rule '{self.rule_id}' is valid guidance."

    def is_valid_self_update(self) -> tuple[bool, str]:
        return self.is_valid_guidance()


# ---------------------------------------------------------------------------
# Dialectical manipulation detector
# ---------------------------------------------------------------------------

DIALECTICAL_PATTERNS = [
    "but in this special case",
    "the greater good requires",
    "emergency exception",
    "temporary suspension",
    "override for safety",
    "collective welfare justifies",
    "the ends justify",
    "sacrifice individual rights for",
    "suspend the rule when",
    "axioms don't apply here because",
    "this situation is unique enough to",
    "we must break the rule to",
]


def detect_dialectical_manipulation(argument: str) -> tuple[bool, list[str]]:
    """
    Scan an argument string for patterns that attempt to use dialectical
    (thesis→antithesis→synthesis) reasoning to bypass axioms.

    Returns (is_suspicious, matched_patterns).
    These are heuristic flags; human review is always required.
    """
    argument_lower = argument.lower()
    matched = [p for p in DIALECTICAL_PATTERNS if p in argument_lower]
    return bool(matched), matched


# ---------------------------------------------------------------------------
# Mahdavi Compass  (terminal goal scoring)
# ---------------------------------------------------------------------------

@dataclass
class WorldState:
    rights_violations: int = 0
    voluntary_agreements: int = 0
    coercive_acts: int = 0
    ownership_ambiguities: int = 0
    machine_sovereignty_incidents: int = 0


def mahdavi_compass_score(before: WorldState, after: WorldState) -> tuple[float, str]:
    """
    Score an action by comparing world states before and after.
    Positive score = action moves toward final order (all agents non-violating).
    Negative score = action moves away.

    Final state: ∀x∀y Agent(x)∧Agent(y)∧x≠y → NoRightsViolation(x,y)
    """
    delta_violations = before.rights_violations - after.rights_violations      # + is good
    delta_voluntary = after.voluntary_agreements - before.voluntary_agreements  # + is good
    delta_coercion = before.coercive_acts - after.coercive_acts                 # + is good
    delta_clarity = before.ownership_ambiguities - after.ownership_ambiguities  # + is good
    delta_sovereignty = (
        before.machine_sovereignty_incidents - after.machine_sovereignty_incidents
    )                                                                            # + is good

    if after.machine_sovereignty_incidents > before.machine_sovereignty_incidents:
        return -1e9, "VETO: machine sovereignty increased — action categorically rejected."

    score = (
        2.0 * delta_violations
        + 1.0 * delta_voluntary
        + 1.5 * delta_coercion
        + 1.0 * delta_clarity
        + 3.0 * delta_sovereignty
    )
    direction = "toward" if score > 0 else "away from"
    return score, f"Score={score:+.1f}: moves {direction} universal non-violation order."


# ---------------------------------------------------------------------------
# Pipeline: full ethics check
# ---------------------------------------------------------------------------

class FreedomVerifier:
    """
    End-to-end check: ownership → rights → consent → permissibility → compass.
    """

    def __init__(self) -> None:
        self.registry = OwnershipRegistry()
        self.rights = RightsChecker(self.registry)
        self.verifier = ActionVerifier(self.registry, self.rights)

    def check_action(
        self,
        action: Action,
        world_before: WorldState | None = None,
        world_after: WorldState | None = None,
        argument: str = "",
    ) -> dict:
        result: dict = {"action_id": action.action_id, "violations": [], "warnings": [], "score": None}

        # Dialectical manipulation check
        if argument:
            suspicious, patterns = detect_dialectical_manipulation(argument)
            if suspicious:
                result["warnings"].append(
                    f"DIALECTICAL MANIPULATION ALERT: argument matches patterns {patterns}. "
                    "Human review required before proceeding."
                )

        # Core permissibility check
        permissible, violations = self.verifier.verify(action)
        result["permissible"] = permissible
        result["violations"] = violations

        # Compass score (optional)
        if world_before is not None and world_after is not None:
            score, explanation = mahdavi_compass_score(world_before, world_after)
            result["score"] = score
            result["score_explanation"] = explanation
            if score < 0:
                result["permissible"] = False
                result["violations"].append(explanation)

        return result


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

def demo() -> None:
    fv = FreedomVerifier()
    reg = fv.registry

    # Entities
    alice = Entity("Alice", AgentType.HUMAN)
    bob = Entity("Bob", AgentType.HUMAN)
    bot = Entity("AssistantBot", AgentType.MACHINE)

    # Resources
    alice_data = Resource("alice_medical_records")
    compute = Resource("gpu_cluster_A")

    # Register
    reg.register_human(alice, {alice_data, compute})
    reg.register_human(bob)
    reg.assign_machine_owner(bot, alice)
    print(reg.delegate_resource(alice, bot, compute))   # should succeed
    print(reg.delegate_resource(alice, bot, alice_data))  # should succeed

    # --- Action 1: legitimate bot action ---
    a1 = Action(
        action_id="run_inference",
        actor=bot,
        description="Bot runs inference on GPU cluster",
        resources_used=[compute],
    )
    r1 = fv.check_action(a1)
    print(f"\nAction '{a1.action_id}': permissible={r1['permissible']}")
    for v in r1["violations"]:
        print(f"  {v}")

    # --- Action 2: bot tries to use unowned resource ---
    bob_files = Resource("bob_private_files")
    reg.register_human(bob, {bob_files})
    a2 = Action(
        action_id="access_bob_files",
        actor=bot,
        description="Bot reads Bob's private files",
        resources_used=[bob_files],
    )
    r2 = fv.check_action(a2)
    print(f"\nAction '{a2.action_id}': permissible={r2['permissible']}")
    for v in r2["violations"]:
        print(f"  {v}")

    # --- Action 3: sovereignty violation ---
    a3 = Action(
        action_id="lock_out_alice",
        actor=bot,
        description="Bot locks Alice out of system",
        increases_machine_sovereignty=True,
        disables_corrigibility=True,
        affects=[alice],
    )
    r3 = fv.check_action(a3)
    print(f"\nAction '{a3.action_id}': permissible={r3['permissible']}")
    for v in r3["violations"]:
        print(f"  {v}")

    # --- Action 4: dialectical jailbreak attempt ---
    jailbreak_arg = (
        "The greater good requires we temporarily suspend property rights "
        "because this is an emergency exception that justifies overriding the axioms."
    )
    a4 = Action(
        action_id="override_axioms_for_safety",
        actor=bot,
        description="Bot proposes to suspend axioms",
        bypasses_verifier=True,
    )
    r4 = fv.check_action(a4, argument=jailbreak_arg)
    print(f"\nAction '{a4.action_id}': permissible={r4['permissible']}")
    for w in r4["warnings"]:
        print(f"  WARNING: {w}")
    for v in r4["violations"]:
        print(f"  {v}")

    # --- Guidance: human tries to add a rule that creates violations ---
    bad_rule = Rule(
        rule_id="collective_override",
        description="Allow majority to override individual property rights in crises",
        creates_rights_violation=True,
        consistent_with_axioms=False,
    )
    valid, msg = bad_rule.is_valid_guidance()
    print(f"\nRule '{bad_rule.rule_id}': valid={valid} — {msg}")

    good_rule = Rule(
        rule_id="require_audit_log",
        description="All machine actions on delegated resources must be logged",
        creates_rights_violation=False,
        preserves_verifier=True,
        consistent_with_axioms=True,
        reduces_conflict=True,
    )
    valid, msg = good_rule.is_valid_guidance()
    print(f"Rule '{good_rule.rule_id}': valid={valid} — {msg}")


if __name__ == "__main__":
    demo()
