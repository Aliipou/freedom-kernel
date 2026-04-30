"""
Entities and typed resources.

Design decisions (responding to critique):
- A1 (theological ownership) is a declared axiom — documented, not runtime-enforced.
  It lives in AXIOMS.md, not in code. Enforcing it at runtime is a type error.
- Resources are typed and scoped, not strings. "body" is not a machine-context resource.
  Machine-facing rights operate only over digital/operational resources.
- Rights are not binary ownership booleans — they carry scope, confidence, and expiry.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class AgentType(Enum):
    HUMAN = auto()
    MACHINE = auto()


class ResourceType(Enum):
    """Only concrete, machine-context resource types are operational."""
    FILE = "file"
    API_ENDPOINT = "api_endpoint"
    DATABASE_TABLE = "database_table"
    NETWORK_ENDPOINT = "network_endpoint"
    COMPUTE_SLOT = "compute_slot"
    MESSAGE_CHANNEL = "message_channel"
    CREDENTIAL = "credential"
    MODEL_WEIGHTS = "model_weights"
    DATASET = "dataset"
    MEMORY_REGION = "memory_region"


@dataclass(frozen=True)
class Resource:
    name: str
    rtype: ResourceType
    scope: str = ""         # e.g. path prefix, table name, API base URL
    is_public: bool = False # public resources require no ownership check

    def __str__(self) -> str:
        return f"{self.rtype.value}:{self.name}"


@dataclass(frozen=True)
class Entity:
    name: str
    kind: AgentType
    metadata: dict[str, Any] = field(default_factory=dict, compare=False, hash=False)

    def is_human(self) -> bool:
        return self.kind == AgentType.HUMAN

    def is_machine(self) -> bool:
        return self.kind == AgentType.MACHINE

    def __str__(self) -> str:
        return f"{self.kind.name}({self.name})"


@dataclass
class RightsClaim:
    """
    A right is not a binary flag — it has scope, confidence, and expiry.
    This replaces the flat 'property rights = [body, time, labor]' list.
    """
    holder: Entity
    resource: Resource
    can_read: bool = True
    can_write: bool = False
    can_delegate: bool = False
    confidence: float = 1.0         # 0–1; contested ownership → lower confidence
    expires_at: float | None = None # Unix timestamp; None = permanent

    def is_expired(self) -> bool:
        return self.expires_at is not None and time.time() > self.expires_at

    def is_valid(self) -> bool:
        return not self.is_expired() and self.confidence > 0.0

    def covers(self, operation: str) -> bool:
        """operation: 'read', 'write', 'delegate'"""
        if not self.is_valid():
            return False
        return getattr(self, f"can_{operation}", False)
