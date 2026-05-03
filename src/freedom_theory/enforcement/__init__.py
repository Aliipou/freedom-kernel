"""
Enforcement layer — puts the verifier in the mandatory execution path.

Three layers, increasing strength:

    L1  CapabilityEnforcer   Python audit hook — mandatory for Python-level I/O
    L2  WasmAgentRunner      WASM VM — mandatory for all agent code (requires wasmtime)
    L3  install_agent_profile  seccomp BPF — mandatory at the syscall level (Linux only)

See ENFORCEMENT.md for the full threat model of each layer.
"""
from freedom_theory.enforcement.hooks import CapabilityEnforcer, EnforcementLevel
from freedom_theory.enforcement.wasm_sandbox import WasmAgentRunner, WasmSandboxError

__all__ = [
    "CapabilityEnforcer",
    "EnforcementLevel",
    "WasmAgentRunner",
    "WasmSandboxError",
]
