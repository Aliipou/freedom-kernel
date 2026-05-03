# Freedom Kernel

**Capability-secure mediation runtime for autonomous agents.**

[![CI](https://github.com/Aliipou/freedom-kernel/actions/workflows/ci.yml/badge.svg)](https://github.com/Aliipou/freedom-kernel/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![Rust](https://img.shields.io/badge/core-Rust-orange.svg)](freedom-kernel/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What this is — precisely

A **capability-oriented policy mediation runtime** with experimental confinement layers and partial formal verification.

| | This project | A capability kernel |
|---|---|---|
| Enforcement | Caller must invoke the verifier | The capability IS the access token |
| Confinement | Python audit hook + optional WASM/seccomp | OS-enforced, mandatory |
| Capability model | Process-local logical objects | Hardware tags (CHERI), kernel tables (seL4), FD rights (Capsicum) |
| Bypass | Ignore the result; C extensions; same-process code | Requires compromising the OS kernel |
| Claimed TCB | ~330 LOC in `engine.rs` | Formally proved implementation |

**`kernel-grade` is a roadmap destination, not a description of the current state.**
The enforcement is not yet mandatory end-to-end. Five known gaps follow.

---

## Two branches

| Branch | Scope | Audience |
|---|---|---|
| [`main`](https://github.com/Aliipou/freedom-kernel/tree/main) | SDK — integrate the capability gate into agent frameworks | Developers building agent systems |
| [`kernel-grade`](https://github.com/Aliipou/freedom-kernel/tree/kernel-grade) | Hardening path toward a formally audited enforcement primitive | Security researchers, systems engineers |

---

## Five known gaps

### Gap 1 — Effective attack surface >> stated TCB

The formal TCB is ~330 LOC (`engine.rs`, `wire.rs`, `crypto.rs`). The effective trusted runtime includes:

- Python interpreter and standard library
- PyO3 bindings between Rust and Python
- `OwnershipRegistry`, `Action`, `Entity` Python object model
- All serialization and deserialization paths
- Enforcement glue (`hooks.py`, `wasm_sandbox.py`)

A bug in PyO3 type conversion, Python object serialization, or the enforcement adapter layer can produce wrong results at the enforcement point even if `engine.rs` is correct. The 330-line number describes the formal verification scope, not the attack surface.

### Gap 2 — Declared flags are self-attestation, not detection

```python
Action(deceives=True)   # → BLOCKED
Action(deceives=False)  # → NOT BLOCKED — regardless of what the action actually does
```

A rational adversary will not set `deceives=True`. The runtime enforces declarations; it does not detect violations of them. These flags are **policy metadata** useful for auditing and compliance annotation. They are not adversarial security guarantees.

Detecting whether an action is semantically deceptive or constitutes authority amplification requires a learned classifier or a formal model of agent intent. This project does not solve that problem and does not claim to.

### Gap 3 — Capability objects are process-local, not OS-level

The `CapabilityStore` / `Capability` model provides **process-local logical unforgeability** within a single Python process. It is not the same as:

- **CHERI**: capability = hardware-tagged fat pointer; enforced by the CPU at every load/store
- **Capsicum**: capability = kernel file descriptor with right mask; enforced at every syscall
- **seL4**: capability = entry in a kernel-managed CNode table; enforced at every IPC

Any code in the same process — C extensions, ctypes, native libraries — can bypass the Python object model entirely. The `__setattr__` guard prevents accidental mutation, not a motivated attacker with native access.

### Gap 4 — No formal refinement proof

```
Lean spec  satisfies  stated properties    ✓  proved (FreedomKernel.lean)
Rust impl  satisfies  stated properties    ✓  bounded (Kani harnesses)
Lean spec  ↔  Rust impl                   ✗  not proved — hand-written correspondence
```

If a Lean type does not faithfully mirror the Rust type, the Lean proofs prove properties of a different system. See [`PROOFS.md`](PROOFS.md) for the concrete example (`kind` enum in Lean vs `String == "MACHINE"` in Rust). Closing this gap requires `aeneas` or equivalent. Planned; not done.

### Gap 5 — seccomp handles syscalls; nothing else

The L3 seccomp profile blocks dangerous syscalls. It does not address logic bugs, confused deputy attacks, IPC-based privilege escalation, shared memory abuse, filesystem namespace tricks, or covert channels. Real confinement requires namespaces, Landlock, pledge/unveil, microVM isolation, or a capability OS design. seccomp is one layer, not a confinement primitive.

---

## What this project does provide

**Structural authority attenuation**: A capability derived from a read-only parent cannot have write rights — AND-logic in `Rights.attenuate()` is structural, not checked at runtime. Verified by 18 tests and Kani harnesses.

**Revocation cascade**: `cap.revoke()` transitively revokes all derived capabilities. Verified by concurrent race tests.

**Process-local unforgeability**: External code cannot forge a valid `Capability` without the store's 256-bit random secret. Post-construction mutation of `_rights` raises `AttributeError` — a real slot-mutation vulnerability found and fixed by adversarial testing.

**Policy-level flag enforcement**: A declared blocked flag is blocked unconditionally — no override. Proved by Kani harnesses on the Rust engine for all bounded inputs.

**Mandatory Python-layer I/O mediation (L1)**: `sys.addaudithook` fires before every `open()`, `subprocess.Popen()`, `socket.connect()`. Cannot be removed. Bypassed by C extensions.

**Adversarially tested**: 29 tests, 9 attack categories. One real bug found before external review.

---

## Hardening roadmap

The path from "policy mediation runtime" to "capability enforcement kernel":

| Phase | Goal | Status |
|---|---|---|
| R1 | Rust-only verifier core — `engine.rs` as standalone crate, no PyO3 in TCB | Planned |
| R2 | Python moved entirely outside TCB — all host code untrusted by construction | Planned |
| R3 | Capability-passing IPC — agents communicate via capability tokens, not shared objects | Planned |
| R4 | WASM-only untrusted agents — all agent code isolated in WASM VM | Planned |
| R5 | Coverage-guided fuzzing — AFL++/libFuzzer 72-hour run with no crashes | Planned |
| R6 | Formal refinement proof — Lean spec proved to faithfully model `engine.rs` via `aeneas` | Planned |
| R7 | External audit — independent review by cryptographers, formal methods, OS engineers | Planned |

Current TCB minimization work:

| Phase | Goal | Status |
|---|---|---|
| K2 | Remove all `.unwrap()` from `engine.rs` | Done |
| K3 | Kani proof: `engine.rs` never panics for any input | Planned |
| K4 | Constant-time claim lookup | Planned |

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

### L2 — WASM sandbox

```python
from freedom_theory.enforcement import WasmAgentRunner

runner = WasmAgentRunner(verifier, agent=bot)
runner.load("agent.wasm")    # requires wasmtime-py
result = runner.call("run_task")
```

Agent code runs in a WASM VM. All OS access goes through verified host functions.
C extensions and native libraries cannot load inside the VM.

### L3 — seccomp syscall filter (Linux only)

```python
from freedom_theory.enforcement.seccomp import install_agent_profile
install_agent_profile()   # irreversible; fork first if needed

from freedom_theory.enforcement.seccomp import generate_docker_seccomp_profile
# docker run --security-opt seccomp=agent_seccomp.json ...
```

---

## Access models

### Model A — policy mediation

```
owner registers claim in registry
agent presents: (actor name, resource name, operation)
verifier: registry lookup → check declared flags → PERMITTED / BLOCKED
```

Name-based. The agent presents a name; the registry is consulted at runtime. Used by `FreedomVerifier`. Susceptible to TOCTOU if the registry is not frozen before the verification window.

### Model B — capability objects

```python
from freedom_theory import CapabilityStore

store = CapabilityStore()
cap = store.issue(resource, can_read=True, can_write=True, can_delegate=True)
read_cap = cap.delegate(can_read=True, can_write=False)

store.verify_capability(read_cap, "read")   # True
store.verify_capability(read_cap, "write")  # False

cap.revoke()
store.verify_capability(read_cap, "read")   # False — revoked
```

Token-based within one process. No registry lookup. Scope: process-local logical authority. See Gap 3.

---

## Declared-flag blocks

Policy metadata: if declared `True`, blocked unconditionally. Not adversarial detection (see Gap 2).

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

`tests/test_adversarial.py` — 29 tests, 9 categories. One real vulnerability found (slot mutation → rights amplification):

| Category | Coverage |
|---|---|
| Capability forgery | Hand-crafted secrets, brute force, pickle, deepcopy, slot mutation |
| Authority amplification | Delegation without rights, multi-hop escalation, scratch construction |
| Confused deputy | Actor identity substitution, adapter elevation |
| TOCTOU | Live registry gap, `freeze()` defense, revocation immediacy |
| Revocation races | Concurrent revoke + verify, concurrent revoke + delegate |
| Replay attacks | No-nonce gap documented, audit log detection |
| Serialization attacks | Unknown kwargs, zero-confidence claims, expired claims |
| Monkey patching | Python-layer bypass (documented), L1 hook independence |
| Privilege escalation | All 10 flags individually, flag + valid claim, ownerless machine |

---

## TCB and formal verification

**Stated TCB** (~330 LOC):

| File | Lines | Role |
|---|---|---|
| `freedom-kernel/src/engine.rs` | ~200 | Core verification logic — pure Rust, no I/O |
| `freedom-kernel/src/wire.rs` | ~80 | JSON wire types |
| `freedom-kernel/src/crypto.rs` | ~50 | ed25519 signing |

**Effective attack surface**: Python 69% of codebase by LOC. TCB is the formal scope, not the runtime boundary.

**Formal verification**:

| Tool | Scope | Strength |
|---|---|---|
| Kani | 5 harnesses on Rust source; bounded inputs | Strong for bounded depth |
| Lean 4 | 5 lemmas on Lean specification | Strong for the model; refinement gap unproved |
| TLA+ | State machine invariants | Model only |

```bash
cargo kani --harness prop_forbidden_flags_always_block
```

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

src/freedom_theory/
  kernel/
    capability.py     process-local capability object model
  enforcement/
    hooks.py          L1: Python audit hook
    wasm_sandbox.py   L2: WASM agent runner
    seccomp.py        L3: seccomp profile + Docker/OCI
  extensions/         IFC, detection, synthesis, compass
  adapters/           OpenAI, Anthropic, LangChain, AutoGen

tests/
  test_adversarial.py   29-test attack suite (9 categories)
  test_capability.py    18 tests: four capability invariants
  test_enforcement.py   L1/L2/L3 enforcement

formal/
  freedom_kernel.tla    TLA+ specification
  FreedomKernel.lean    Lean 4 proofs
  plan_semantics.md     Tractability boundary

ARCHITECTURE.md   System architecture; research framing
ENFORCEMENT.md    L0–L3 enforcement design
PROOFS.md         What is and is not proved; refinement gap analysis
THREAT_MODEL.md   Adversary model, trust boundaries, enforcement gap
TCB.md            TCB scope; minimization roadmap
SECURITY.md       Responsible disclosure; audit scope
```

---

## Installation

```bash
pip install freedom-theory-ai                    # pure Python
cd freedom-kernel && pip install .               # with Rust core
pip install wasmtime                             # L2 WASM sandbox
pip install seccomp                              # L3 syscall filter (Linux)
```

---

## External review

The five gaps are the highest-value targets:

- **Cryptographers**: `crypto.rs` — key reuse, replay, forgery?
- **Formal methods**: Where does the hand-written Lean ↔ Rust correspondence break?
- **Systems engineers**: Panic paths, race conditions, unsafe assumptions in the PyO3 layer?
- **Security auditors**: Can you bypass a declared flag in `engine.rs`? Can you amplify a capability from outside `CapabilityStore`?
- **OS engineers**: What is the minimal change that makes enforcement mandatory rather than advisory?

`tests/test_adversarial.py` documents the attack surface as currently understood. Findings that go beyond it are exactly what the project needs. Findings are publicly credited. See [`SECURITY.md`](SECURITY.md).

---

## License

MIT. See [LICENSE](LICENSE).
