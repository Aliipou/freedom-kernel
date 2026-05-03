"""
Enforcement layer — puts the verifier in the mandatory execution path.

Current implementation: Python audit hook (soft enforcement).
Stronger options: WASM sandbox, OS seccomp (see ENFORCEMENT.md).

The hook intercepts Python-level resource access (file open, subprocess,
network). It cannot block C extensions calling the OS directly. For full
isolation, use the WASM backend or OS-level process confinement.
"""
from freedom_theory.enforcement.hooks import CapabilityEnforcer, EnforcementLevel

__all__ = ["CapabilityEnforcer", "EnforcementLevel"]
