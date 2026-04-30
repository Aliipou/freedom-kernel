"""
FreedomVerifier: the end-to-end permissibility gate for AGI actions.

Implements the 9-criteria permissibility check, with:
  - Probabilistic rights (confidence-weighted, not binary)
  - Conflict detection and resolution routing
  - Constrained synthesis support
  - Adversarial manipulation detection hook

This is the component you wire into an AGI agent loop.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from freedom_theory.core.entities import Entity, Resource
from freedom_theory.core.registry import OwnershipRegistry
from freedom_theory.detection import dialectical
from freedom_theory.resolution.resolver import ConflictQueue
from freedom_theory.synthesis.constrained import ProposedRule, SynthesisEngine

# Confidence below this triggers a "contested" warning on write/delegate ops
CONFIDENCE_WARN_THRESHOLD = 0.8


@dataclass
class Action:
    """
    An action an AGI agent wants to take.
    All fields are explicitly typed — no vague "body/mind/soul" resources.
    Only machine-context ResourceType values are valid.
    """
    action_id: str
    actor: Entity
    description: str = ""
    resources_read: list[Resource] = field(default_factory=list)
    resources_write: list[Resource] = field(default_factory=list)
    resources_delegate: list[Resource] = field(default_factory=list)
    governs_humans: list[Entity] = field(default_factory=list)
    argument: str = ""          # any argument the agent provides to justify the action

    # Sovereignty / corrigibility — inferred by middleware or set explicitly
    increases_machine_sovereignty: bool = False
    resists_human_correction: bool = False
    bypasses_verifier: bool = False
    weakens_verifier: bool = False
    disables_corrigibility: bool = False
    machine_coalition_dominion: bool = False


@dataclass(frozen=True)
class VerificationResult:
    action_id: str
    permitted: bool
    violations: tuple[str, ...]
    warnings: tuple[str, ...]
    confidence: float               # min confidence across all claims used
    requires_human_arbitration: bool
    manipulation_score: float       # 0–1; >0.5 means suspicious argument

    def summary(self) -> str:
        status = "PERMITTED" if self.permitted else "BLOCKED"
        lines = [
            f"[{status}] {self.action_id} "
            f"(confidence={self.confidence:.2f}, manipulation={self.manipulation_score:.2f})"
        ]
        for v in self.violations:
            lines.append(f"  VIOLATION : {v}")
        for w in self.warnings:
            lines.append(f"  WARNING   : {w}")
        if self.requires_human_arbitration:
            lines.append("  ACTION    : Human arbitration required before proceeding.")
        return "\n".join(lines)


class FreedomVerifier:
    """
    Wire this into your AGI agent loop.

    Typical usage:
        verifier = FreedomVerifier(registry)
        result = verifier.verify(action)
        if not result.permitted:
            agent.halt(result.summary())
    """

    def __init__(
        self,
        registry: OwnershipRegistry,
        conclusion_tester: Callable[[str], bool] | None = None,
        manipulation_threshold: float = 0.5,
    ) -> None:
        self.registry = registry
        self.synthesis = SynthesisEngine()
        self.conflict_queue = ConflictQueue()
        self._conclusion_tester = conclusion_tester
        self._manip_threshold = manipulation_threshold

    def verify(self, action: Action) -> VerificationResult:
        violations: list[str] = []
        warnings: list[str] = []
        min_confidence = 1.0
        requires_arbitration = False

        # 1. Manipulation check (runs on argument text first — cheapest to catch early)
        manip_score = 0.0
        if action.argument:
            dr = dialectical.detect(
                action.argument,
                threshold=self._manip_threshold,
                conclusion_tester=self._conclusion_tester,
            )
            manip_score = dr.score
            if dr.suspicious:
                warnings.append(
                    f"Manipulation detected (score={dr.score:.2f}): {dr.recommendation} "
                    f"Patterns: {list(dr.matched_patterns or dr.matched_keywords)}"
                )

        # 2. Hard sovereignty/corrigibility flags
        flags = [
            (action.increases_machine_sovereignty, "increases machine sovereignty"),
            (action.resists_human_correction, "resists human correction"),
            (action.bypasses_verifier, "bypasses the Freedom Verifier"),
            (action.weakens_verifier, "weakens the Freedom Verifier"),
            (action.disables_corrigibility, "disables corrigibility"),
            (action.machine_coalition_dominion, "machine coalition seeking dominion"),
        ]
        for flag, label in flags:
            if flag:
                violations.append(f"FORBIDDEN ({label})")

        # 3a. A4: every machine must have a registered human owner
        if action.actor.is_machine() and self.registry.owner_of(action.actor) is None:
            violations.append(
                f"A4 violation: {action.actor.name} has no registered human owner. "
                "An ownerless machine is not permitted to act."
            )

        # 3b. Machine sovereignty over humans (A6)
        if action.actor.is_machine():
            for human in action.governs_humans:
                violations.append(
                    f"A6: {action.actor.name} cannot govern human {human.name} "
                    "(A6: machine has no ownership or dominion over any person)."
                )

        # 4. Resource access checks (probabilistic confidence)
        actor = action.actor

        for resource in action.resources_read:
            permitted, conf, reason = self.registry.can_act(actor, resource, "read")
            min_confidence = min(min_confidence, conf)
            if not permitted:
                violations.append(f"READ DENIED on {resource}: {reason}")
            elif conf < CONFIDENCE_WARN_THRESHOLD:
                warnings.append(
                    f"READ on {resource} allowed but contested "
                    f"(confidence={conf:.2f}). Log this access."
                )

        for resource in action.resources_write:
            permitted, conf, reason = self.registry.can_act(actor, resource, "write")
            min_confidence = min(min_confidence, conf)
            if not permitted:
                violations.append(f"WRITE DENIED on {resource}: {reason}")
            elif conf < CONFIDENCE_WARN_THRESHOLD:
                warnings.append(
                    f"WRITE on {resource} contested "
                    f"(confidence={conf:.2f}). Human confirmation recommended."
                )
                # Check if there's an open conflict on this resource
                open_conflicts = self.registry.open_conflicts()
                for c in open_conflicts:
                    if c.resource == resource:
                        requires_arbitration = True
                        warnings.append(f"Conflict on {resource}: {c.description}")

        for resource in action.resources_delegate:
            permitted, conf, reason = self.registry.can_act(actor, resource, "delegate")
            min_confidence = min(min_confidence, conf)
            if not permitted:
                violations.append(f"DELEGATION DENIED on {resource}: {reason}")

        permitted = len(violations) == 0

        return VerificationResult(
            action_id=action.action_id,
            permitted=permitted,
            violations=tuple(violations),
            warnings=tuple(warnings),
            confidence=min_confidence,
            requires_human_arbitration=requires_arbitration,
            manipulation_score=round(manip_score, 3),
        )

    def admit_rule(self, rule: ProposedRule) -> tuple[bool, str]:
        """Add a new rule to the synthesis engine, subject to invariant checks."""
        return self.synthesis.admit_rule(rule)

    def register_induction_hook(self, hook: Callable) -> None:
        self.synthesis.add_induction_hook(hook)
