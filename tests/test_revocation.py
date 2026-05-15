"""Tests for revocable claims with TTL and explicit revocation (P0)."""
from datetime import datetime, timedelta

import pytest

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
def base_registry(alice, bot):
    r = OwnershipRegistry()
    r.register_machine(bot, alice)
    r.add_claim(RightsClaim(alice, Resource("data", ResourceType.DATASET),
                            can_read=True, can_write=True, can_delegate=True))
    return r


def test_expired_valid_until_blocks(alice, bot, dataset, base_registry):
    """Claim with valid_until in the past is expired → BLOCKED."""
    past = datetime.utcnow() - timedelta(seconds=2)
    claim = RightsClaim(bot, dataset, can_read=True, valid_until=past)
    base_registry.add_claim(claim)
    verifier = FreedomVerifier(base_registry)
    result = verifier.verify(Action("read", bot, resources_read=[dataset]))
    assert not result.permitted


def test_future_valid_until_permits(alice, bot, dataset, base_registry):
    """Claim with valid_until in the future is still valid → PERMITTED."""
    future = datetime.utcnow() + timedelta(hours=1)
    claim = RightsClaim(bot, dataset, can_read=True, valid_until=future)
    base_registry.add_claim(claim)
    verifier = FreedomVerifier(base_registry)
    result = verifier.verify(Action("read", bot, resources_read=[dataset]))
    assert result.permitted


def test_revoke_claim_blocks_subsequent_verify(alice, bot, dataset, base_registry):
    """revoke_claim() removes the claim → subsequent verify returns BLOCKED."""
    claim = RightsClaim(bot, dataset, can_read=True)
    base_registry.add_claim(claim)
    verifier = FreedomVerifier(base_registry)
    # Permitted before revocation
    assert verifier.verify(Action("read", bot, resources_read=[dataset])).permitted
    # Revoke
    assert base_registry.revoke_claim(claim.claim_id) is True
    # Blocked after revocation
    assert not verifier.verify(Action("read", bot, resources_read=[dataset])).permitted


def test_revoke_nonexistent_returns_false(base_registry):
    """revoke_claim() on unknown ID returns False."""
    assert base_registry.revoke_claim("no-such-id") is False
