"""
Freedom Kernel — Capability-security operating layer for autonomous agents.

Architecture:
  kernel/     — minimal formal gate (FreedomVerifier, ExecutionContext, GoalNode)
  adapters/   — framework adapters (OpenAI, Anthropic, LangChain, AutoGen)
  extensions/ — pluggable layers on top (manipulation detection, synthesis, compass)
"""
from freedom_theory.adapters.anthropic import AnthropicKernelAdapter
from freedom_theory.adapters.autogen import AutoGenKernelAdapter
from freedom_theory.adapters.langchain import FreedomTool, kernel_gate
from freedom_theory.adapters.openai_agents import OpenAIKernelMiddleware
from freedom_theory.extensions import (
    ExtendedFreedomVerifier,
    IFCViolation,
    NonInterferenceChecker,
    SecurityLattice,
)
from freedom_theory.extensions.compass import CompassScore, WorldState
from freedom_theory.extensions.compass import score as compass_score
from freedom_theory.extensions.compass import score_action as compass_score_action
from freedom_theory.extensions.emergency import EmergencyContext, EmergencyProtocol
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
from freedom_theory.kernel.audit import AuditLog
from freedom_theory.kernel.entities import A2ViolationError, ConsentRecord
from freedom_theory.kernel.context import ExecutionContext
from freedom_theory.kernel.goals import GoalNode, GoalVerificationResult, verify_goal_tree
from freedom_theory.kernel.policy import Policy, PolicyRule, PolicyVerifier

__all__ = [
    # Core kernel
    "A2ViolationError",
    "ConsentRecord",
    "AgentType",
    "Entity",
    "Resource",
    "ResourceType",
    "RightsClaim",
    "ConflictRecord",
    "OwnershipRegistry",
    "Action",
    "FreedomVerifier",
    "VerificationResult",
    # Stage 2: bounded contexts + goal verification
    "ExecutionContext",
    "GoalNode",
    "GoalVerificationResult",
    "verify_goal_tree",
    # Stage 3: framework adapters
    "OpenAIKernelMiddleware",
    "AnthropicKernelAdapter",
    "FreedomTool",
    "kernel_gate",
    "AutoGenKernelAdapter",
    # Policy IR
    "Policy",
    "PolicyRule",
    "PolicyVerifier",
    # Extensions
    "ExtendedFreedomVerifier",
    "WorldState",
    "compass_score",
    "CompassScore",
    "compass_score_action",
    "detect_manipulation",
    "ProposedRule",
    "SynthesisEngine",
    "EmergencyProtocol",
    "EmergencyContext",
    # IFC
    "IFCViolation",
    "NonInterferenceChecker",
    "SecurityLattice",
    # Audit
    "AuditLog",
]
