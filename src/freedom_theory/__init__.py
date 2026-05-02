"""
Freedom Kernel — Capability-security operating layer for autonomous agents.

Architecture:
  kernel/     — minimal formal gate (FreedomVerifier, ExecutionContext)
  extensions/ — pluggable layers on top (manipulation detection, synthesis, compass)
"""
from freedom_theory.extensions import ExtendedFreedomVerifier
from freedom_theory.extensions.compass import WorldState
from freedom_theory.extensions.compass import score as compass_score
from freedom_theory.extensions.detection import detect as detect_manipulation
from freedom_theory.extensions.synthesis import ProposedRule, SynthesisEngine
from freedom_theory.kernel import (
    Action,
    AgentType,
    ConflictRecord,
    Entity,
    FreedomVerifier,
    OwnershipRegistry,
    Resource,
    ResourceType,
    RightsClaim,
    VerificationResult,
)
from freedom_theory.kernel.context import ExecutionContext

__all__ = [
    "AgentType",
    "Entity",
    "Resource",
    "ResourceType",
    "RightsClaim",
    "ConflictRecord",
    "OwnershipRegistry",
    "Action",
    "FreedomVerifier",
    "ExtendedFreedomVerifier",
    "VerificationResult",
    "ExecutionContext",
    "WorldState",
    "compass_score",
    "detect_manipulation",
    "ProposedRule",
    "SynthesisEngine",
]
