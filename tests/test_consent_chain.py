"""Tests for ConsentChain — traceable consent for cross-human resource access (P1)."""
from datetime import datetime, timedelta

import pytest

from freedom_theory.kernel.entities import (
    AgentType, ConsentRecord, Entity, Resource, ResourceType, RightsClaim
)
from freedom_theory.kernel.registry import OwnershipRegistry
from freedom_theory.kernel.verifier import Action, FreedomVerifier


@pytest.fixture
def alice():
    return Entity("Alice", AgentType.HUMAN)


@pytest.fixture
def bob():
    return Entity("Bob", AgentType.HUMAN)


@pytest.fixture
def shared_data():
    return Resource("shared", ResourceType.DATASET)


@pytest.fixture
def registry(alice, bob, shared_data):
    r = OwnershipRegistry()
    r.add_claim(RightsClaim(alice, shared_data, can_read=True, can_write=True))
    r.add_claim(RightsClaim(bob, shared_data, can_read=True, can_write=True))
    return r


def test_no_consent_record_adds_warning(alice, bob, shared_data, registry):
    """No ConsentRecord from Bob when Alice reads shared resource → WARNING (backward compat)."""
    verifier = FreedomVerifier(registry)
    action = Action("read-shared", alice, resources_read=[shared_data])
    result = verifier.verify(action)
    assert result.permitted
    assert any("ConsentRecord" in w for w in result.warnings)


def test_valid_consent_record_no_warning(alice, bob, shared_data, registry):
    """Valid ConsentRecord from Bob: no consent warning."""
    verifier = FreedomVerifier(registry)
    consent = ConsentRecord(grantor=bob, scope=shared_data.scope)
    action = Action(
        "read-shared", alice,
        resources_read=[shared_data],
        consent_records=[consent],
    )
    result = verifier.verify(action)
    assert result.permitted
    assert not any("ConsentRecord" in w for w in result.warnings)


def test_expired_consent_record_blocks(alice, bob, shared_data, registry):
    """Expired ConsentRecord from Bob → BLOCKED."""
    verifier = FreedomVerifier(registry)
    past = datetime.utcnow() - timedelta(seconds=2)
    consent = ConsentRecord(grantor=bob, scope=shared_data.scope, expires_at=past)
    action = Action(
        "read-shared", alice,
        resources_read=[shared_data],
        consent_records=[consent],
    )
    result = verifier.verify(action)
    assert not result.permitted
    assert any("expired" in v.lower() for v in result.violations)
