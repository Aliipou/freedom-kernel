"""
Entities and typed resources.

A1 (theological ownership) is a declared axiom — documented, not runtime-enforced.
Resources are typed and scoped, not strings.
Rights carry scope, confidence, and expiry — not binary ownership booleans.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Optional
from uuid import uuid4


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
    # Theory-grounded property types (A3 enumeration)
    IDENTITY      = 'identity'
    REPUTATION    = 'reputation'
    TIME_QUOTA    = 'time_quota'
    PERSON        = 'person'
    COMMUNICATION = 'communication'
    FINANCIAL     = 'financial'


class A2ViolationError(ValueError):
    """Raised when a claim would violate A2 (no human owns another human)."""


@dataclass(frozen=True)
class Resource:
    name: str
    rtype: ResourceType
    scope: str = ""
    is_public: bool = False
    ifc_label: str = field(default="", compare=False, hash=False)

    def __str__(self) -> str:
        return f"{self.rtype.value}:{self.name}"


def scope_contains(parent_scope: str, child_path: str) -> bool:
    """
    Returns True iff child_path falls within parent_scope (prefix matching).

    Formal rule: scope_contains(P, C) iff C == P or C starts with normalize(P) + "/"
    An empty parent_scope matches everything (root / universal scope).
    """
    if not parent_scope:
        return True
    normalized = parent_scope.rstrip("/")
    return child_path == normalized or child_path.startswith(normalized + "/")


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
class ConsentRecord:
    """A3: valid_consent requires informed, voluntary, specific, revocable consent."""
    grantor:    Entity
    scope:      str
    informed:   bool = True
    voluntary:  bool = True
    specific:   bool = True
    granted_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    record_id:  str = field(default_factory=lambda: str(uuid4()))

    def is_valid(self) -> bool:
        """A3: all consent conditions must hold and not be expired."""
        return (
            self.informed
            and self.voluntary
            and self.specific
            and (self.expires_at is None or datetime.utcnow() < self.expires_at)
        )


@dataclass
class RightsClaim:
    """A right is not a binary flag — it has scope, confidence, and expiry."""
    holder: Entity
    resource: Resource
    can_read: bool = True
    can_write: bool = False
    can_delegate: bool = False
    confidence: float = 1.0
    expires_at: float | None = None
    claim_id:    str = field(default_factory=lambda: str(uuid4()))
    valid_from:  Optional[datetime] = None
    valid_until: Optional[datetime] = None

    def is_expired(self) -> bool:
        return self.expires_at is not None and time.time() > self.expires_at

    def is_active(self, at: Optional[datetime] = None) -> bool:
        """Check datetime-based validity window (A7: claims must be valid at time of use)."""
        now = at or datetime.utcnow()
        if self.valid_from and now < self.valid_from:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        return True

    def is_valid(self) -> bool:
        return not self.is_expired() and self.confidence > 0.0 and self.is_active()

    def covers(self, operation: str) -> bool:
        if not self.is_valid():
            return False
        return getattr(self, f"can_{operation}", False)
