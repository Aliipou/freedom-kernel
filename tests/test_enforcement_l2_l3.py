"""L2 and L3 enforcement tests — WASM sandbox and seccomp profile."""
import json
import platform

import pytest

from freedom_theory.enforcement.seccomp import generate_docker_seccomp_profile
from freedom_theory.enforcement.wasm_sandbox import WasmAgentRunner, WasmSandboxError
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
    allowed = Resource(name="report.txt", rtype=ResourceType.FILE)
    registry = OwnershipRegistry()
    registry.register_machine(bot, alice)
    registry.add_claim(RightsClaim(holder=bot, resource=allowed, can_read=True))
    return FreedomVerifier(registry), bot


# ── L2: WASM sandbox ─────────────────────────────────────────────────────────

def test_wasm_runner_level():
    assert WasmAgentRunner.level() == "L2-wasm"


def test_wasm_runner_requires_module_before_call():
    verifier, bot = _setup()
    runner = WasmAgentRunner(verifier, agent=bot)
    with pytest.raises(WasmSandboxError, match="No module loaded"):
        runner.call("run")


def test_wasm_runner_load_raises_without_wasmtime(tmp_path, monkeypatch):
    """load() raises WasmSandboxError with a clear message if wasmtime is absent."""
    import builtins
    real_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "wasmtime":
            raise ImportError("wasmtime not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)

    verifier, bot = _setup()
    runner = WasmAgentRunner(verifier, agent=bot)
    fake_wasm = tmp_path / "agent.wasm"
    fake_wasm.write_bytes(b"\x00asm\x01\x00\x00\x00")  # minimal WASM header

    with pytest.raises(WasmSandboxError, match="wasmtime-py is required"):
        runner.load(str(fake_wasm))


# ── L3: seccomp profile ───────────────────────────────────────────────────────

def test_seccomp_docker_profile_is_valid_json():
    profile_json = generate_docker_seccomp_profile()
    profile = json.loads(profile_json)
    assert profile["defaultAction"] == "SCMP_ACT_ERRNO"
    assert "syscalls" in profile
    allowed = profile["syscalls"][0]["names"]
    assert "read" in allowed
    assert "write" in allowed


def test_seccomp_docker_profile_denies_dangerous_syscalls():
    profile = json.loads(generate_docker_seccomp_profile())
    allowed = set(profile["syscalls"][0]["names"])
    # These must NOT be in the allow list
    for dangerous in ("socket", "execve", "ptrace", "mount", "bpf"):
        assert dangerous not in allowed, f"{dangerous} must not be in allow list"


def test_seccomp_install_requires_linux():
    from freedom_theory.enforcement.seccomp import install_agent_profile
    if platform.system() == "Linux":
        pytest.skip("Would actually install seccomp filter — skip on Linux CI")
    with pytest.raises(RuntimeError, match="Linux"):
        install_agent_profile()
