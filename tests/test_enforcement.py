"""
Enforcement hook tests.

sys.addaudithook() is permanent — hooks cannot be removed. Tests that call
install() must suspend the enforcer before returning so the hook does not
interfere with pytest file reads during session cleanup.

Most tests call _audit_hook() directly to verify decision logic without
triggering the system-wide hook mechanism.
"""
import pytest

from freedom_theory.enforcement import CapabilityEnforcer, EnforcementLevel
from freedom_theory.kernel import (
    AgentType,
    Entity,
    FreedomVerifier,
    OwnershipRegistry,
    Resource,
    ResourceType,
    RightsClaim,
)


def _setup():
    alice   = Entity(name="alice", kind=AgentType.HUMAN)
    bot     = Entity(name="bot",   kind=AgentType.MACHINE)
    allowed = Resource(name="allowed.txt", rtype=ResourceType.FILE)
    secret  = Resource(name="secret.txt",  rtype=ResourceType.FILE)
    registry = OwnershipRegistry()
    registry.register_machine(bot, alice)
    registry.add_claim(RightsClaim(holder=bot, resource=allowed, can_read=True, can_write=True))
    verifier = FreedomVerifier(registry)
    return verifier, bot, allowed, secret


def _enforcer(verifier, bot):
    """Create an enforcer that is installed but immediately suspended."""
    e = CapabilityEnforcer(verifier, agent=bot)
    e.install()
    e.suspend()
    return e


def test_enforcer_level_is_soft():
    assert CapabilityEnforcer.level() == EnforcementLevel.SOFT


def test_enforcer_blocks_read_without_claim():
    verifier, bot, allowed, secret = _setup()
    e = _enforcer(verifier, bot)
    e.resume()
    try:
        with pytest.raises(PermissionError, match="secret.txt"):
            e._audit_hook("open", ("secret.txt", "r"))
    finally:
        e.suspend()


def test_enforcer_permits_read_with_claim():
    verifier, bot, allowed, secret = _setup()
    e = _enforcer(verifier, bot)
    e.resume()
    try:
        e._audit_hook("open", ("allowed.txt", "r"))  # must not raise
    finally:
        e.suspend()


def test_enforcer_blocks_write_without_claim():
    verifier, bot, allowed, secret = _setup()
    e = _enforcer(verifier, bot)
    e.resume()
    try:
        with pytest.raises(PermissionError, match="secret.txt"):
            e._audit_hook("open", ("secret.txt", "w"))
    finally:
        e.suspend()


def test_enforcer_permits_write_with_claim():
    verifier, bot, allowed, secret = _setup()
    e = _enforcer(verifier, bot)
    e.resume()
    try:
        e._audit_hook("open", ("allowed.txt", "w"))  # must not raise
    finally:
        e.suspend()


def test_enforcer_blocks_subprocess():
    verifier, bot, allowed, secret = _setup()
    e = _enforcer(verifier, bot)
    e.resume()
    try:
        with pytest.raises(PermissionError, match="/bin/sh"):
            e._audit_hook("subprocess.Popen", (["/bin/sh", "-c", "ls"],))
    finally:
        e.suspend()


def test_enforcer_suspend_disables_hook():
    verifier, bot, allowed, secret = _setup()
    e = _enforcer(verifier, bot)
    # Suspended — secret.txt should not raise
    e._audit_hook("open", ("secret.txt", "r"))


def test_enforcer_agent_swap():
    """Swapping the agent changes what is enforced without reinstalling."""
    verifier, bot, allowed, secret = _setup()
    alice2 = Entity(name="alice2", kind=AgentType.HUMAN)
    bot2   = Entity(name="bot2",   kind=AgentType.MACHINE)
    registry2 = OwnershipRegistry()
    registry2.register_machine(bot2, alice2)
    verifier2 = FreedomVerifier(registry2)

    e = _enforcer(verifier, bot)
    e.resume()
    try:
        # bot has claim — permitted
        e._audit_hook("open", ("allowed.txt", "r"))
        # Swap verifier to one where bot has no claims
        e.verifier = verifier2
        with pytest.raises(PermissionError):
            e._audit_hook("open", ("allowed.txt", "r"))
    finally:
        e.suspend()


def test_enforcer_ignores_unknown_events():
    verifier, bot, allowed, secret = _setup()
    e = _enforcer(verifier, bot)
    e.resume()
    try:
        # Unknown audit events should not raise
        e._audit_hook("import", ("os",))
        e._audit_hook("compile", ("source", "filename"))
    finally:
        e.suspend()
