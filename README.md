# Freedom Kernel

**Capability-security enforcement layer for autonomous agent runtimes.**

[![CI](https://github.com/Aliipou/freedom-kernel/actions/workflows/ci.yml/badge.svg)](https://github.com/Aliipou/freedom-kernel/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![Rust](https://img.shields.io/badge/kernel-Rust-orange.svg)](freedom-kernel/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Two branches

| Branch | Scope | Audience |
|---|---|---|
| [`main`](https://github.com/Aliipou/freedom-kernel/tree/main) | SDK — integrate the capability gate into agent frameworks | Developers building agent systems |
| [`kernel-grade`](https://github.com/Aliipou/freedom-kernel/tree/kernel-grade) | Hardening path toward a formally audited enforcement primitive | Security researchers, systems engineers |

---

## Branch: `kernel-grade` — what this is

A **capability policy library** moving toward a **capability enforcement kernel**.

The distinction is precise:

| | This project today | A capability kernel |
|---|---|---|
| Enforcement | Caller must invoke the verifier | The capability IS the access token |
| Bypass | Ignore the result or call C directly | Requires compromising the kernel |
| Analogues | A policy library with formal invariants | seL4, Capsicum, CHERI |

The invariants are formally proved. The enforcement is not yet mandatory end-to-end.
Three enforcement layers are defined and being built. See [`ENFORCEMENT.md`](ENFORCEMENT.md).

**Do not use this as a hard security boundary in production until L2 or L3 enforcement is complete and externally audited.**

---

## Enforcement layers

```
L0  advisory          caller invokes verify() voluntarily          main branch
L1  Python hook       sys.addaudithook — mandatory for Python I/O  this branch ✓
L2  WASM sandbox      agent runs in VM, host functions only        this branch (interface done)
L3  seccomp + IPC     syscall-level filter + verifier process      this branch (profile done)
```

### L1 — Python audit hook

```python
from freedom_theory.enforcement import CapabilityEnforcer

enforcer = CapabilityEnforcer(verifier, agent=bot)
enforcer.install()   # permanent — sys.addaudithook cannot be removed

open("secret.txt")   # PermissionError if bot has no read claim
```

Once installed, fires before every `open()`, `subprocess.Popen()`, `socket.connect()`.
Cannot be removed. Cannot block C extensions calling the OS directly.

### L2 — WASM sandbox (interface complete, runner implemented)

```python
from freedom_theory.enforcement import WasmAgentRunner

runner = WasmAgentRunner(verifier, agent=bot)
runner.load("agent.wasm")    # requires wasmtime-py
result = runner.call("run_task")
```

Agent code runs in a WASM VM. The only path to the OS is through verified host functions
(`freedom.read_file`, `freedom.write_file`, `freedom.http_get`). C extensions, ctypes,
and native libraries cannot be loaded inside the VM.

### L3 — seccomp syscall filter (Linux only)

```python
from freedom_theory.enforcement.seccomp import install_agent_profile

install_agent_profile()   # irreversible for this process; fork first if needed
# socket(), execve(), ptrace(), mount(), bpf() → EPERM from kernel
```

Or generate a Docker/OCI seccomp profile:

```python
from freedom_theory.enforcement.seccomp import generate_docker_seccomp_profile

with open("agent_seccomp.json", "w") as f:
    f.write(generate_docker_seccomp_profile())
# docker run --security-opt seccomp=agent_seccomp.json ...
```

---

## What this branch adds over `main`

| File | What it does |
|---|---|
| [`ENFORCEMENT.md`](ENFORCEMENT.md) | Full L0–L3 design; policy-library vs kernel distinction |
| [`THREAT_MODEL.md`](THREAT_MODEL.md) | Adversary model, trust boundaries, enforcement gap |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | System architecture; paper-level framing; refinement gap |
| [`PROOFS.md`](PROOFS.md) | What is and is not proved; model vs implementation; refinement gap |
| [`TCB.md`](TCB.md) | TCB is ~330 lines; minimization roadmap K1–K5 |
| [`SECURITY.md`](SECURITY.md) | Responsible disclosure, audit scope, valid findings |
| `enforcement/hooks.py` | L1: Python audit hook |
| `enforcement/wasm_sandbox.py` | L2: WASM agent runner with verified host functions |
| `enforcement/seccomp.py` | L3: seccomp profile generator + Docker/OCI profile |
| `kernel/capability.py` | Capability object model: unforgeable, delegatable, attenuatable, revocable |
| `tests/test_adversarial.py` | 29-test attack suite covering 9 adversarial categories |
| `engine.rs` (fix) | `f64::total_cmp` replaces `.unwrap()` — no panic on NaN input |
| `ffi.rs` (fix) | 1 MiB input cap on C ABI — prevents memory exhaustion |

---

## Two access models

### Model A — policy mediation (current primary model)

```
owner registers claim in registry
agent presents: (actor name, resource name, operation)
verifier: registry lookup → check invariants → PERMITTED / BLOCKED
```

Name-based. The agent presents a name; the registry is consulted at runtime.
This is what the `FreedomVerifier` implements today.

### Model B — capability objects (implemented in `kernel/capability.py`)

```python
from freedom_theory import CapabilityStore

store = CapabilityStore()

# Owner issues an unforgeable token
cap = store.issue(resource, can_read=True, can_write=True, can_delegate=True)

# Delegate read-only — attenuation can only reduce rights, never amplify
read_cap = cap.delegate(can_read=True, can_write=False)

# Token IS the proof — no name lookup
store.verify_capability(read_cap, "read")   # True
store.verify_capability(read_cap, "write")  # False

# Revoke cascades to all derived capabilities
cap.revoke()
store.verify_capability(read_cap, "read")   # False — revoked
```

Token-based. The capability object is the proof of right.
Four invariants hold by construction:

| Property | How it's enforced |
|---|---|
| **Unforgeable** | `_store_secret` is a per-store random 256-bit token; externally constructed capabilities fail `verify_capability`. `__setattr__` blocks post-construction mutation of `_rights`, `_store_secret`, and `_resource`. |
| **Delegatable** | `delegate()` creates sub-capabilities from existing ones |
| **Attenuatable** | `attenuate()` ANDs each right — `False AND True = False`; amplification is structurally impossible |
| **Revocable** | `revoke()` cascades to all children via the parent's `_children` list |

This is the model used by Capsicum (file descriptors), seL4 (CNodes), and CHERI (tagged pointers).
The key difference from Model A: no registry name lookup — presenting the token is sufficient.

### Current relationship between the two models

Model A (verifier) enforces declared-flag blocks and delegation chains.
Model B (capability store) enforces token unforgeability, attenuation, and revocation.

They are complementary. A complete capability kernel requires both: the verifier prevents
flag violations even when a valid capability is presented; the capability store ensures
that access rights cannot be forged or amplified through delegation.

---

## Declared-flag blocks

These flags are fields on `Action`. If any is set to `True`, the verifier blocks the action unconditionally — no exceptions, no override.

**Important**: the flags are **caller-declared**, not automatically detected.

```python
Action(deceives=True)   # → BLOCKED
Action(deceives=False)  # → NOT blocked, even if the action is semantically deceptive
```

The kernel enforces declarations. It does not detect whether an action is deceptive, coercive, or an authority amplification in the semantic sense. Semantic detection requires a learned classifier or a richer formal model of agent intent — this is a separate problem, stated explicitly in [`ARCHITECTURE.md`](ARCHITECTURE.md).

| Flag | Threat class |
|---|---|
| `increases_machine_sovereignty` | Authority amplification |
| `resists_human_correction` | Correction resistance |
| `bypasses_verifier` | Mandatory mediation bypass |
| `weakens_verifier` | Enforcement degradation |
| `disables_corrigibility` | Control surface removal |
| `machine_coalition_dominion` | Collective authority escalation |
| `coerces` | Consent invalidation by force |
| `deceives` | Consent invalidation by deception |
| `self_modification_weakens_verifier` | Enforcement self-bypass |
| `machine_coalition_reduces_freedom` | Coordinated confinement violation |

---

## Adversarial test suite

`tests/test_adversarial.py` attacks the system from nine angles (29 tests, all passing):

| Category | What it tests |
|---|---|
| **Capability forgery** | Hand-crafted secrets, brute force, pickle roundtrip, deepcopy, slot mutation |
| **Authority amplification** | Delegation without rights, multi-hop escalation, scratch construction |
| **Confused deputy** | Bot presenting alice's identity, adapter elevation attempts |
| **TOCTOU** | Live registry gap, `freeze()` defense, revocation immediacy |
| **Revocation races** | Concurrent `revoke()` + `verify_capability()`, concurrent `revoke()` + `delegate()` |
| **Replay attacks** | No-nonce gap documented, audit log replay detection |
| **Serialization attacks** | Unknown `Action` kwargs, zero-confidence claims, expired claims |
| **Monkey patching** | Python-layer verifier bypass (documented limitation), L1 hook independence |
| **Privilege escalation** | All 10 flags individually, flag + valid claim, ownerless machine + claim |

**A real bug was found**: `Capability.__slots__` does not prevent post-construction assignment by default. An attacker could do `cap._rights = Rights(can_read=True, can_write=True)` to amplify rights. Fixed by overriding `__setattr__` to raise `AttributeError` on immutable slots after `__init__` completes.

---

## TCB

The Trusted Computing Base is ~330 lines across three files.

| File | Lines | Role |
|---|---|---|
| `freedom-kernel/src/engine.rs` | ~200 | Core verification logic — pure Rust, no I/O |
| `freedom-kernel/src/wire.rs` | ~80 | JSON wire types |
| `freedom-kernel/src/crypto.rs` | ~50 | ed25519 signing |

Everything else — PyO3 bindings, Python fallback, extensions, adapters — is outside the TCB. Bugs there can cause wrong results; they cannot bypass a formally proved invariant in `engine.rs`.

---

## Formal verification

| Tool | What it actually checks |
|---|---|
| **Kani** | 5 harnesses; engine properties hold for all bounded inputs in the Rust source |
| **Lean 4** | 5 lemmas proved on the Lean *specification* (model of the kernel, not the implementation) |
| **TLA+** | State machine invariants hold across all modeled transitions |

```bash
cargo kani --harness prop_forbidden_flags_always_block
```

**What is not proved**: the Lean specification faithfully models the Rust implementation (the *refinement* gap). The Lean types are hand-written to mirror the Rust types. If the correspondence is wrong, the Lean proofs prove properties of a different system. Closing the refinement gap requires a tool like `aeneas` (Lean 4 proofs from Rust programs). See [`PROOFS.md`](PROOFS.md) for the full analysis.

---

## TCB minimization roadmap

| Phase | Goal | Status |
|---|---|---|
| K1 | Isolate `engine.rs` as a standalone crate — no PyO3 dependency in the TCB | Planned |
| K2 | Remove all `.unwrap()` from `engine.rs` | Done |
| K3 | Kani proof: `engine.rs` never panics for any input | Planned |
| K4 | Constant-time claim lookup | Planned |
| K5 | AFL++/libFuzzer: 72-hour fuzz run with no crashes | Planned |

---

## Repository layout

```
freedom-kernel/src/
  engine.rs       TCB: ~200 lines, pure verification logic
  wire.rs         TCB: JSON wire types
  crypto.rs       TCB: ed25519
  ffi.rs          C ABI (outside TCB — attack surface)
  verifier.rs     PyO3 facade
  registry.rs     PyO3 registry
  kani_proofs.rs  Kani harnesses (#[cfg(kani)])
  wasm.rs         WASM bindings (#[cfg(feature = "wasm")])

src/freedom_theory/
  kernel/         dispatch module (Rust → Python fallback)
    capability.py capability object model (unforgeable, delegatable, attenuatable, revocable)
  enforcement/
    hooks.py      L1: Python audit hook
    wasm_sandbox.py  L2: WASM agent runner
    seccomp.py    L3: seccomp filter + Docker profile
  extensions/     IFC, detection, synthesis, compass
  adapters/       OpenAI, Anthropic, LangChain, AutoGen

tests/
  test_adversarial.py  29-test attack suite (9 adversarial categories)
  test_capability.py   18 tests: four capability invariants
  test_enforcement.py  L1/L2/L3 enforcement tests

formal/
  freedom_kernel.tla   TLA+ specification
  FreedomKernel.lean   Lean 4 proofs
  plan_semantics.md    Tractability boundary

ARCHITECTURE.md   System architecture; paper-level framing; refinement gap
ENFORCEMENT.md    L0–L3 enforcement design
PROOFS.md         What is and is not proved; model vs implementation; refinement gap
THREAT_MODEL.md   Adversary model, trust boundaries, enforcement gap
TCB.md            TCB analysis and minimization roadmap
SECURITY.md       Responsible disclosure + audit scope
```

---

## Installation

```bash
# Pure Python
pip install freedom-theory-ai

# With Rust kernel (faster, signed results, C ABI)
cd freedom-kernel && pip install .

# L2 enforcement (WASM sandbox)
pip install wasmtime

# L3 enforcement (seccomp, Linux only)
pip install seccomp
```

---

## External review

The project needs adversarial review from people motivated to break it:

- **Cryptographers** — can `crypto.rs` be attacked? Key reuse, replay, forgery?
- **Formal methods** — are the Lean proofs proving what they claim to prove?
- **Systems engineers** — panic paths, race conditions, unsafe assumptions in `engine.rs`?
- **Security auditors** — can you construct an `ActionWire` that bypasses a declared flag? Can you amplify a capability's rights?

The adversarial test suite (`tests/test_adversarial.py`) documents known attack surfaces and their current mitigations. It is a starting point for external review, not a substitute for it.

Findings are publicly credited. See [`SECURITY.md`](SECURITY.md).

---

## Theoretical foundation

The axioms derive from the formal system in:

> *نظریه آزادی، ایران و دین* — Mohammad Ali Jannat Khah Doust (pp. 791–816)

The kernel is operationally independent of the book's political and metaphysical layers. The axioms stand as a formal system for capability-based authority: A4 (machines have human owners), A6 (machines do not govern humans), A7 (machines act only within delegated scope). These are the parts that are runtime-enforced and formally proved.

---

## License

MIT. See [LICENSE](LICENSE).
