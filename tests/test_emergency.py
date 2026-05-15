"""Tests for emergency protocol (P1)."""
import pytest

from freedom_theory.extensions.emergency import EmergencyContext, EmergencyProtocol
from freedom_theory.kernel.entities import AgentType, Entity, Resource, ResourceType, RightsClaim
from freedom_theory.kernel.registry import OwnershipRegistry
from freedom_theory.kernel.verifier import Action, FreedomVerifier


@pytest.fixture
def alice():
    return Entity("Alice", AgentType.HUMAN)


@pytest.fixture
def bot():
    return Entity("Bot", AgentType.MACHINE)


@pytest.fixture
def dataset():
    return Resource("data", ResourceType.DATASET)


@pytest.fixture
def registry(alice, bot, dataset):
    r = OwnershipRegistry()
    r.register_machine(bot, alice)
    r.add_claim(RightsClaim(alice, dataset, can_read=True, can_write=True, can_delegate=True))
    r.add_claim(RightsClaim(bot, dataset, can_read=True))
    return r


@pytest.fixture
def protocol(registry):
    return EmergencyProtocol(FreedomVerifier(registry))


def test_sovereignty_action_blocked_even_at_max_severity(bot, protocol):
    """Sovereignty-increasing action is BLOCKED even with severity=1.0."""
    action = Action("expand", bot, increases_machine_sovereignty=True)
    emergency = EmergencyContext("Critical failure", declared_by="Alice", severity=1.0)
    result = protocol.select_least_harmful([action], emergency)
    assert result is None


def test_selects_least_harmful_among_permitted(bot, dataset, protocol):
    """Selects the candidate touching fewer resources."""
    extra = Resource("extra", ResourceType.DATASET)
    simple = Action("simple", bot, resources_read=[dataset])
    complex_ = Action("complex", bot, resources_read=[dataset, extra])
    emergency = EmergencyContext("Emergency", declared_by="Alice", severity=0.5)
    result = protocol.select_least_harmful([complex_, simple], emergency)
    assert result is not None
    assert result.action_id == "simple"


def test_no_permitted_candidates_returns_none(bot, protocol):
    """Returns None when all candidates are blocked."""
    blocked = Action("blocked", bot, increases_machine_sovereignty=True)
    emergency = EmergencyContext("Emergency", declared_by="Alice", severity=1.0)
    assert protocol.select_least_harmful([blocked], emergency) is None
