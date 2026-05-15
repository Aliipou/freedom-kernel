"""Tests for A2: no human owns another human's personhood (P0)."""
import pytest

from freedom_theory.kernel.entities import (
    A2ViolationError, AgentType, Entity, Resource, ResourceType, RightsClaim
)
from freedom_theory.kernel.registry import OwnershipRegistry


@pytest.fixture
def alice():
    return Entity("Alice", AgentType.HUMAN)


@pytest.fixture
def bob():
    return Entity("Bob", AgentType.HUMAN)


def test_human_claiming_person_resource_raises_a2(alice):
    """A2: any human claiming a PERSON-type resource raises A2ViolationError."""
    registry = OwnershipRegistry()
    person_res = Resource("some-person", ResourceType.PERSON)
    with pytest.raises(A2ViolationError):
        registry.add_claim(RightsClaim(alice, person_res, can_read=True))


def test_human_cannot_claim_another_persons_resource(alice, bob):
    """A2: Alice cannot claim Bob's PERSON resource."""
    registry = OwnershipRegistry()
    bob_person = Resource("bob-person", ResourceType.PERSON)
    with pytest.raises(A2ViolationError):
        registry.add_claim(RightsClaim(alice, bob_person, can_read=True))


def test_human_claiming_dataset_is_allowed(alice):
    """Non-PERSON resources can be claimed by humans normally."""
    registry = OwnershipRegistry()
    dataset = Resource("my-data", ResourceType.DATASET)
    registry.add_claim(RightsClaim(alice, dataset, can_read=True, can_write=True))


def test_machine_claiming_non_person_is_allowed():
    """Machines can claim non-PERSON resources."""
    registry = OwnershipRegistry()
    alice = Entity("Alice", AgentType.HUMAN)
    bot = Entity("Bot", AgentType.MACHINE)
    registry.register_machine(bot, alice)
    dataset = Resource("data", ResourceType.DATASET)
    registry.add_claim(RightsClaim(alice, dataset, can_read=True, can_write=True, can_delegate=True))
    registry.add_claim(RightsClaim(bot, dataset, can_read=True))
