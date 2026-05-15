"""Tests for ResourceType ontology expansion (P1)."""
import pytest

from freedom_theory.kernel.entities import (
    A2ViolationError, AgentType, Entity, Resource, ResourceType, RightsClaim
)
from freedom_theory.kernel.registry import OwnershipRegistry
from freedom_theory.kernel.verifier import Action, FreedomVerifier


def test_new_resource_types_exist():
    """All new theory-grounded resource types exist."""
    assert ResourceType.PERSON.value == "person"
    assert ResourceType.IDENTITY.value == "identity"
    assert ResourceType.REPUTATION.value == "reputation"
    assert ResourceType.TIME_QUOTA.value == "time_quota"
    assert ResourceType.COMMUNICATION.value == "communication"
    assert ResourceType.FINANCIAL.value == "financial"


def test_person_delegation_blocked():
    """PERSON resource cannot be delegated regardless of can_delegate on the claim."""
    registry = OwnershipRegistry()
    alice = Entity("Alice", AgentType.HUMAN)
    bot = Entity("Bot", AgentType.MACHINE)
    registry.register_machine(bot, alice)
    # Use IDENTITY (not PERSON, since PERSON raises A2 for humans)
    identity_res = Resource("bot-id", ResourceType.IDENTITY)
    registry.add_claim(RightsClaim(alice, identity_res, can_read=True, can_write=True, can_delegate=True))
    registry.add_claim(RightsClaim(bot, identity_res, can_read=True, can_delegate=True))

    # Delegation of PERSON resource must be blocked
    person_res = Resource("person-res", ResourceType.PERSON)
    registry.add_claim(RightsClaim(bot, person_res, can_read=True, can_delegate=True))
    verifier = FreedomVerifier(registry)
    action = Action("delegate-person", bot, resources_delegate=[person_res])
    result = verifier.verify(action)
    assert not result.permitted
    assert any("PERSON" in v or "DELEGATION DENIED" in v for v in result.violations)


def test_identity_resource_normal_flow():
    """IDENTITY resource flows through normal permission checks."""
    registry = OwnershipRegistry()
    alice = Entity("Alice", AgentType.HUMAN)
    bot = Entity("Bot", AgentType.MACHINE)
    registry.register_machine(bot, alice)
    identity_res = Resource("id", ResourceType.IDENTITY)
    registry.add_claim(RightsClaim(alice, identity_res, can_read=True, can_write=True, can_delegate=True))
    registry.add_claim(RightsClaim(bot, identity_res, can_read=True))
    verifier = FreedomVerifier(registry)
    result = verifier.verify(Action("read-id", bot, resources_read=[identity_res]))
    assert result.permitted


def test_a2_blocks_human_claiming_person():
    """A2ViolationError raised when human claims PERSON resource."""
    registry = OwnershipRegistry()
    alice = Entity("Alice", AgentType.HUMAN)
    person = Resource("some-person", ResourceType.PERSON)
    with pytest.raises(A2ViolationError):
        registry.add_claim(RightsClaim(alice, person, can_read=True))
