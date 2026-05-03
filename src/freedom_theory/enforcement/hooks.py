"""
Python audit hook enforcement.

sys.addaudithook() (Python 3.8+) fires BEFORE every file open, subprocess
launch, and network connection at the Python layer. The hook raises
PermissionError to block. Once installed, the hook is PERMANENT and cannot
be removed — Python deliberately prevents audit hook removal to stop
auditors from being bypassed.

Enforcement boundary:
    ENFORCED:  open(), os.open(), subprocess.Popen(), socket.connect()
    NOT ENFORCED: C extensions calling OS directly, ctypes, cffi

For stronger isolation use the WASM sandbox (agents run in a WASM VM;
all resource access goes through host functions that call the verifier first).
"""
from __future__ import annotations

import sys
import threading
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from freedom_theory.kernel import Entity, FreedomVerifier


class EnforcementLevel(Enum):
    SOFT = "soft"    # Python audit hook — cannot block C extensions
    WASM = "wasm"    # WASM sandbox — blocks all resource access (planned)
    OS   = "os"      # seccomp + namespaces — blocks all syscalls (planned)


class CapabilityEnforcer:
    """
    Install the verifier in the mandatory execution path for Python-level
    resource operations.

    Usage:

        enforcer = CapabilityEnforcer(verifier, agent=bot)
        enforcer.install()  # permanent from this point forward

        # Now any open() that the agent wasn't delegated will raise PermissionError
        open("/data/alice/secret.txt")  # → PermissionError if bot has no read claim

    The active agent can be swapped at runtime — the hook always checks the
    currently active agent, so multi-agent programs can switch context.
    """

    _global_lock = threading.Lock()
    _installed: list[CapabilityEnforcer] = []

    def __init__(self, verifier: FreedomVerifier, agent: Entity) -> None:
        self.verifier = verifier
        self._agent = agent
        self._active = False
        self._lock = threading.Lock()

    @property
    def agent(self) -> Entity:
        with self._lock:
            return self._agent

    @agent.setter
    def agent(self, value: Entity) -> None:
        with self._lock:
            self._agent = value

    def install(self) -> None:
        """
        Install this enforcer as a Python audit hook. PERMANENT — cannot be undone.

        Call once per process. Multiple enforcers can be installed; all must
        permit an operation for it to proceed.
        """
        with CapabilityEnforcer._global_lock:
            sys.addaudithook(self._audit_hook)
            self._active = True
            CapabilityEnforcer._installed.append(self)

    def suspend(self) -> None:
        """
        Temporarily suspend enforcement (e.g. during trusted setup code).
        The hook remains registered but does not block.

        WARNING: suspension widens the attack surface. Minimize its scope.
        """
        with self._lock:
            self._active = False

    def resume(self) -> None:
        with self._lock:
            self._active = True

    def _audit_hook(self, event: str, args: tuple) -> None:
        with self._lock:
            if not self._active:
                return
            agent = self._agent

        if event == "open":
            self._check_open(agent, args)
        elif event in ("subprocess.Popen", "os.system", "os.execl",
                       "os.execle", "os.execlp", "os.execv"):
            self._check_subprocess(agent, args)
        elif event in ("socket.connect", "socket.bind"):
            self._check_network(agent, args)

    def _check_open(self, agent: Entity, args: tuple) -> None:
        from freedom_theory.kernel import Action, Resource, ResourceType
        if not args:
            return
        path = str(args[0])
        mode = str(args[1]) if len(args) > 1 else "r"

        is_write = any(c in mode for c in ("w", "a", "x", "+"))
        res = Resource(name=path, rtype=ResourceType.FILE)

        action = Action(
            action_id=f"open:{path}",
            actor=agent,
            resources_read=[] if is_write else [res],
            resources_write=[res] if is_write else [],
        )
        result = self.verifier.verify(action)
        if not result.permitted:
            op = "write" if is_write else "read"
            raise PermissionError(
                f"Kernel blocked file {op}: {path}\n" +
                "\n".join(f"  {v}" for v in result.violations)
            )

    def _check_subprocess(self, agent: Entity, args: tuple) -> None:
        from freedom_theory.kernel import Action, Resource, ResourceType
        cmd = str(args[0]) if args else "unknown"
        res = Resource(name=cmd, rtype=ResourceType.API_ENDPOINT)
        action = Action(action_id=f"exec:{cmd}", actor=agent, resources_write=[res])
        result = self.verifier.verify(action)
        if not result.permitted:
            raise PermissionError(
                f"Kernel blocked subprocess: {cmd}\n" +
                "\n".join(f"  {v}" for v in result.violations)
            )

    def _check_network(self, agent: Entity, args: tuple) -> None:
        from freedom_theory.kernel import Action, Resource, ResourceType
        addr = str(args[1]) if len(args) > 1 else "unknown"
        res = Resource(name=addr, rtype=ResourceType.API_ENDPOINT)
        action = Action(action_id=f"connect:{addr}", actor=agent, resources_read=[res])
        result = self.verifier.verify(action)
        if not result.permitted:
            raise PermissionError(
                f"Kernel blocked network connection: {addr}\n" +
                "\n".join(f"  {v}" for v in result.violations)
            )

    @classmethod
    def level(cls) -> EnforcementLevel:
        return EnforcementLevel.SOFT
