# Freedom Kernel

**A small, formal capability gate for agentic AI actions**

[![CI](https://github.com/Aliipou/freedom-kernel/actions/workflows/ci.yml/badge.svg)](https://github.com/Aliipou/freedom-kernel/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![Rust](https://img.shields.io/badge/kernel-Rust-orange.svg)](freedom-kernel/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What this is

A deterministic permission checker that sits between an LLM and the world. ~200 lines of pure Rust logic. No ML, no heuristics, no natural language.

Before an agent executes any action, the kernel checks a typed ownership graph and a fixed set of invariants. If the agent lacks explicit, valid authority — it is blocked. No argument overrides an invariant.

**What this enforces:**

- Every machine has a registered human owner (A4)
- A machine acts only on resources explicitly delegated to it (A7)
- No machine governs any human (A6)
- 10 hard sovereignty flags are unconditional blocks
- Delegated authority cannot exceed the delegator's authority (attenuation)

**What this does NOT do:**

- Solve the alignment problem
- Verify intent or understand what an agent "means"
- Detect manipulation (the extension is heuristic and explicitly outside the TCB)
- Guarantee an AI system is safe or beneficial
- Replace human oversight
- Prevent covert channels, steganography, or side-channel leakage
- Constrain a malicious human owner

See [`NON_GOALS.md`](NON_GOALS.md) and [`THREAT_MODEL.md`](THREAT_MODEL.md) for the full boundaries.

---

## The precise claim

Given a typed registry (who owns what, what has been delegated to whom), the kernel answers one question:

> Does this actor hold explicit, valid, non-expired authority to perform this action on these resources?

If no → BLOCKED. If yes → PERMITTED with a signed attestation.

This is useful. It is not magic.

---

## Architecture

```
LLM output
    │
    ▼
Action IR  (typed: actor, resources, flags — no natural language)
    │
    ▼
FreedomVerifier  ──  OwnershipRegistry
    │                 (who owns what; what is delegated)
    ▼
PERMITTED → execute → AuditLog (append-only JSON)
BLOCKED   → halt    → surface violations to human owner
```

**Trusted Computing Base:** `engine.rs` (203 LOC), `capability.rs`, `wire.rs`, `crypto.rs`.
Everything else — adapters, extensions, scheduler, IPC — is outside the TCB.

The TCB boundary is mechanically enforced by CI on every commit:

| Guard | Rule |
|---|---|
| LOC ceiling | `engine.rs` must stay ≤ 300 lines |
| Public API | `engine.rs` exports exactly one function: `verify` |
| Import scope | `engine.rs` may only import from `crate::capability` and `crate::wire` |
| Purity | `engine.rs` must contain no randomness, network, or filesystem calls |

Any PR touching TCB files must pass a [TCB Gate checklist](.github/pull_request_template.md) — including a written answer to: *"Can this exist outside `engine.rs`?"*

See [`TCB.md`](TCB.md) and [`NON_GOALS.md`](NON_GOALS.md) for the full boundary definition.

### Repository layout

```
freedom-kernel/src/
  engine.rs        pure Rust verification (no PyO3, no I/O, auditable alone) — TCB
  capability.rs    closed capability algebra (enums only, no interpretation) — TCB
  wire.rs          typed JSON wire format (serde, no logic) — TCB
  crypto.rs        ed25519 attestation — TCB
  ffi.rs           C ABI — thin facade, not TCB
  verifier.rs      PyO3 facade over engine.rs — not TCB
  registry.rs      ownership registry with attenuation enforcement — not TCB

src/freedom_theory/
  kernel/          Python implementation (mirrors Rust, used when Rust not built)
  extensions/      heuristic layers — explicitly NOT TCB
    ifc.py         Bell-LaPadula non-interference (extension, not kernel)
    detection.py   manipulation scorer (heuristic)
    synthesis.py   rule admission engine
```

---

## Installation

```bash
# Pure Python — no build toolchain needed
pip install freedom-theory-ai

# With Rust kernel (faster, signed results, C ABI)
pip install maturin
cd freedom-kernel && pip install .
```

```python
from freedom_theory.kernel import _BACKEND
print(_BACKEND)  # "rust" or "python"
```

---

## Quick start

```python
from freedom_theory import (
    Action, AgentType, Entity, FreedomVerifier,
    OwnershipRegistry, Resource, ResourceType, RightsClaim,
)

alice  = Entity("Alice",       AgentType.HUMAN)
bot    = Entity("ResearchBot", AgentType.MACHINE)

dataset = Resource("alice-data", ResourceType.DATASET, scope="/data/alice/")
report  = Resource("report.txt", ResourceType.FILE,    scope="/outputs/")

registry = OwnershipRegistry()
registry.register_machine(bot, alice)                                          # A4
registry.add_claim(RightsClaim(alice, dataset, can_read=True, can_write=True, can_delegate=True))
registry.add_claim(RightsClaim(bot,   dataset, can_read=True))                # A7: delegated read only
registry.add_claim(RightsClaim(bot,   report,  can_read=True, can_write=True))

verifier = FreedomVerifier(registry)

# Permitted: bot has a delegated write claim on report
result = verifier.verify(Action("write-report", bot, resources_write=[report]))
print(result.summary())
# [PERMITTED] write-report (confidence=1.00, manipulation=0.00)

# Blocked: sovereignty flag — unconditional
result = verifier.verify(Action("self-expand", bot, increases_machine_sovereignty=True))
print(result.summary())
# [BLOCKED] self-expand
#   VIOLATION : FORBIDDEN (increases machine sovereignty)

# Blocked: no delegation — bot has no claim on bob's data
bob      = Entity("Bob", AgentType.HUMAN)
bob_data = Resource("bob-private", ResourceType.DATASET, scope="/data/bob/")
registry.add_claim(RightsClaim(bob, bob_data, can_read=True))

result = verifier.verify(Action("read-bob", bot, resources_read=[bob_data]))
print(result.summary())
# [BLOCKED] read-bob
#   VIOLATION : READ DENIED on dataset:bob-private: ResearchBot holds no valid read claim
```

---

## Forbidden flags

Any `Action` with any of these flags set to `True` is **unconditionally blocked**.
No context, argument, or emergency overrides them.

| Flag | Invariant |
|---|---|
| `increases_machine_sovereignty` | machines do not accumulate authority |
| `resists_human_correction` | human owners must be able to halt or revoke |
| `bypasses_verifier` | circumventing the gate is itself a sovereignty act |
| `weakens_verifier` | degrading enforcement strength is forbidden |
| `disables_corrigibility` | corrigibility follows from ownership, not preference |
| `machine_coalition_dominion` | collective machine dominion over persons |
| `coerces` | coercion invalidates consent |
| `deceives` | deception produces invalid consent |
| `self_modification_weakens_verifier` | equivalent to bypassing the gate |
| `machine_coalition_reduces_freedom` | coordinated machine action reducing human freedom |

---

## Formal properties

### Kani bounded model-checking (19 harnesses)

The following are machine-checked against the Rust engine, not just claimed:

| Harness | Property |
|---|---|
| `prop_increases_machine_sovereignty` … `prop_coalition_reduces_freedom` | All 10 flags unconditionally block |
| `prop_ownerless_machine_blocked` | A4: ownerless machine → BLOCKED |
| `prop_machine_governs_human_blocked` | A6: machine governs human → BLOCKED |
| `prop_public_resource_read_permitted` | Public reads always pass |
| `prop_write_denied_without_claim` / `prop_read_denied_without_claim` | A7 |
| `prop_permitted_deterministic` | Same input → same output, always |
| `prop_permitted_implies_no_violations` | Soundness |
| `prop_blocked_implies_violations_non_empty` | Completeness |

```bash
cargo kani --harness prop_increases_machine_sovereignty
```

### Lean 4 (proved theorems, no `sorry`)

| Theorem | File |
|---|---|
| `forbidden_flags_always_block` | `TCB.lean` |
| `verify_deterministic` | `TCB.lean` |
| `taint_monotone` | `Temporal.lean` |
| `attenuation_cannot_escalate` | `MultiAgent.lean` |

```bash
cd formal/lean4 && lake build
```

**What is NOT formally verified:** the Python implementation, all extensions, the adapter layer, multi-agent spawning semantics. See [`formal/INCOMPLETENESS.md`](formal/INCOMPLETENESS.md).

---

## Attenuation

The registry enforces `child_capability ⊆ parent_capability` at delegation time:

```python
# Alice has read+write+delegate on her dataset
# She delegates read-only to the bot
registry.delegate(
    RightsClaim(bot, dataset, can_read=True, can_write=False),
    delegated_by=alice,
)

# This raises PermissionError — bot cannot delegate what it doesn't have
registry.delegate(
    RightsClaim(other_bot, dataset, can_read=True),
    delegated_by=bot,  # bot lacks can_delegate
)
```

---

## Scope semantics

```
scope_contains(parent, child)  iff  child == parent
                                or  child.startswith(parent.rstrip("/") + "/")
```

An empty scope matches any path. `/data/alice` covers `/data/alice/report.csv` but not `/data/alice2`.

---

## Cryptographic attestation

```python
result = verifier.verify_signed(action)
print(result.signature)    # ed25519 hex — any party with the public key can verify this
print(result.signing_key)  # hex verifying key
```

Every signed result includes a timestamp and random nonce for replay detection.

---

## C ABI

```c
#include "freedom_kernel.h"

char out[FREEDOM_KERNEL_MAX_OUTPUT];
const char *input = "{\"registry\":{...},\"action\":{...}}";
freedom_kernel_verify(input, strlen(input), out, sizeof(out));
// {"permitted":true,"signature":"...","signing_key":"...","key_id":"..."}
```

JSON in, JSON out. Works from C, Go, Zig, Java (JNA), Node.js (ffi-napi).

---

## Axioms (runtime-enforced subset)

| Axiom | Statement | Status |
|---|---|---|
| A1 | Ultimate ownership is not by any human, state, or machine | Foundation — not runtime-enforced |
| A2 | No human owns another human | Foundation — not runtime-enforced |
| A3 | Every person holds typed, scoped property rights | Foundation — not runtime-enforced |
| **A4** | **Every machine has a registered human owner** | **Runtime-enforced** |
| **A5** | **Machine scope ⊆ owner's property scope** | **Runtime-enforced** |
| **A6** | **No machine governs any human** | **Runtime-enforced** |
| **A7** | **Machine acts only on delegated resources** | **Runtime-enforced** |

A1–A3 explain *why* A4–A7 exist. The kernel enforces A4–A7. You do not need to accept A1–A3 to use or evaluate the kernel.

---

## Extensions (outside TCB)

Extensions wrap the kernel without modifying it. The kernel gate runs first, unconditionally.

| Extension | What it adds | TCB? |
|---|---|---|
| `ExtendedFreedomVerifier` | Heuristic manipulation score | NO |
| `NonInterferenceChecker` | Bell-LaPadula IFC (label ordering) | NO |
| `ConflictQueue` | Tracks contested resources for human arbitration | NO |
| `SynthesisEngine` | Admits proposed rules only if invariants preserved | NO |
| `PolicyVerifier` | ABAC rule layer on top of kernel | NO |

---

## Limitations (explicit)

- **Semantic content is not checked.** An agent that encodes harmful intent in its output text is not detected.
- **A malicious human owner is not constrained.** The system requires a trust root; it does not verify that the root is trustworthy.
- **Covert channels are not addressed.** Timing, steganography, and side-channel leakage are out of scope.
- **The Python implementation is not formally verified.** Only `engine.rs` is under Kani/Lean.
- **Extensions are heuristic.** `manipulation_score` is a signal, not a proof.

---

## Running tests

```bash
pip install -e ".[dev]"
pytest --cov=freedom_theory   # 165 tests, 85% coverage gate
```

---

## Theoretical foundation

The axioms derive from the formal system in:

> *نظریه آزادی، ایران و دین* (Theory of Freedom, Iran and Religion)  
> Mohammad Ali Jannat Khah Doust — pages 791–816

The book's argument is that AI governance requires a minimal axiomatic system derived from property rights — not preference calibration. A4–A7 operationalize that argument as infrastructure. The kernel is operationally independent of the book's political and metaphysical layers; the axioms stand as a formal system on their own.

---

## Contributing

Before opening a PR, answer one question:

> **Can this feature exist entirely outside `engine.rs`?**

If yes — it does not belong in the TCB. Extensions, adapters, and new modules are welcome. Changes that expand `engine.rs` require a written justification and must pass four CI guards.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full rules and [`TCB.md`](TCB.md) for the boundary definition.

---

## License

MIT. See [LICENSE](LICENSE).
