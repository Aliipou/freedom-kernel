"""
Freedom Theory AI — Formal Axiomatic Ethics System for AGI

Based on: نظریه آزادی (Theory of Freedom) by Mohammad Ali Jannat Khah Doust

Declared axiom layer (ontological, not runtime-enforced):
  A1: Person(h) → OwnedByGod(h)
      Every person's ultimate ownership is divine — not by state, class, machine, or ideology.
      This is the metaphysical foundation from which A2–A7 derive.
      [It cannot be runtime-enforced; it is declared here as the grounding axiom.]

Operational axiom layer (runtime-enforced, machine-context only):
  A2: No human owns another human.
  A3: Every person has typed, scoped property rights over digital resources they own.
  A4: Every machine has a registered human owner.
  A5: Machine operational scope ⊆ owner's property scope.
  A6: No machine owns or governs any human.
  A7: Machines act only on explicitly delegated resources.

Core principle (from p.801):
  No action may violate legitimate property rights.
"""

from freedom_theory.compass.mahdavi import WorldState
from freedom_theory.compass.mahdavi import score as compass_score
from freedom_theory.core.entities import AgentType, Entity, Resource, ResourceType, RightsClaim
from freedom_theory.core.registry import OwnershipRegistry
from freedom_theory.core.verifier import Action, FreedomVerifier, VerificationResult
from freedom_theory.detection.dialectical import detect as detect_manipulation
from freedom_theory.synthesis.constrained import ProposedRule, SynthesisEngine

__all__ = [
    "AgentType",
    "Entity",
    "Resource",
    "ResourceType",
    "RightsClaim",
    "OwnershipRegistry",
    "Action",
    "FreedomVerifier",
    "VerificationResult",
    "WorldState",
    "compass_score",
    "detect_manipulation",
    "ProposedRule",
    "SynthesisEngine",
]
