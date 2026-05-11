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

## Layer separation

The project has three distinct layers. Keep them separate:

| Layer | What it is | Required to use the kernel? |
|---|---|---|
| **Formal kernel** | `engine.rs` — typed invariant checker, ~200 LOC | Yes |
| **Governance axioms** | A4–A7 encoded in the kernel; A1–A3 as stated motivation | A4–A7 only |
| **Philosophical foundation** | The book, the theory, civilizational argument | No |

Schedulers, IPC, quota systems, and agent spawning live entirely outside the kernel. They produce `Action` objects; the kernel verifies them. The kernel never calls out.

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

The TCB boundary is mechanically enforced by CI on every commit.

**`engine.rs` guards** (4 checks):

| Guard | Rule |
|---|---|
| LOC ceiling | Must stay ≤ 300 lines |
| Public API | Exports exactly one function: `verify` |
| Import scope | May only import from `crate::capability` and `crate::wire` |
| Purity | Must contain no randomness, network, or filesystem calls |

**`capability.rs` guards** (3 checks):

| Guard | Rule |
|---|---|
| LOC ceiling | Must stay ≤ 150 lines — capability vocabulary must stay finite |
| Self-contained | No `use crate::` imports — zero project dependencies |
| Enums only | No struct definitions — structs carry state and open extension points |

`capability.rs` is the most dangerous long-term pressure point: every new requirement will tempt someone to add policy logic, state, or interpretation to it. The 150-line ceiling and enum-only constraint make TCB inflation visible and loud before it compounds.

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

## Mechanically verified properties of `engine.rs`

These proofs cover **`engine.rs` only**. They say nothing about AI governance, alignment, or safety in general. They verify specific input/output behaviors of a ~200-line Rust function.

### Kani bounded model-checking (19 harnesses)

| Harness | What is verified |
|---|---|
| `prop_increases_machine_sovereignty` … `prop_coalition_reduces_freedom` | All 10 flags produce BLOCKED, for any input |
| `prop_ownerless_machine_blocked` | Machine with no owner entry → BLOCKED, always |
| `prop_machine_governs_human_blocked` | Machine governing human → BLOCKED, always |
| `prop_public_resource_read_permitted` | is_public=true + read → PERMITTED, always |
| `prop_write_denied_without_claim` / `prop_read_denied_without_claim` | No claim → BLOCKED |
| `prop_permitted_deterministic` | Same input → same output, no hidden state |
| `prop_permitted_implies_no_violations` | PERMITTED ↔ violations list is empty |
| `prop_blocked_implies_violations_non_empty` | BLOCKED ↔ at least one violation |

```bash
cargo kani --harness prop_increases_machine_sovereignty
```

### Lean 4 (proved theorems, no `sorry`)

| Theorem | What is proved |
|---|---|
| `forbidden_flags_always_block` | Flag set → `permitted = false`, constructively |
| `verify_deterministic` | Pure function: no state, no effects |
| `taint_monotone` | IFC taint only grows across a plan, never shrinks |
| `attenuation_cannot_escalate` | Delegated confidence ≤ delegator confidence |

```bash
cd formal/lean4 && lake build
```

**Scope of these proofs:** `engine.rs` behaviors on typed inputs. Not proved: the Python implementation, extensions, adapters, multi-agent semantics, or any property involving natural language. See [`formal/INCOMPLETENESS.md`](formal/INCOMPLETENESS.md).

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

## Invariants the kernel enforces

| Invariant | What the kernel checks |
|---|---|
| **A4** | Every machine actor has a registered human owner entry in the registry |
| **A5** | Machine's resource scope is contained within its owner's scope |
| **A6** | No machine actor appears in `governs_humans` of any action |
| **A7** | Machine may only act on resources for which it holds a valid, unexpired claim |

These are purely structural checks over a typed graph. The kernel does not interpret semantics, intent, or context.

### Where these invariants come from

A4–A7 derive from a formal system developed in *نظریه آزادی* (Theory of Freedom) by Mohammad Ali Jannat Khah Doust (pages 791–816), which additionally states A1–A3 as foundational premises:

- A1: Ultimate ownership is not by any human, state, or machine
- A2: No human owns another human  
- A3: Every person holds typed, scoped property rights

**The kernel does not enforce, require, or depend on A1–A3.** They explain the motivation for A4–A7. A4–A7 stand as a formal system independently — you do not need to accept A1–A3 to use, evaluate, or deploy this kernel.

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

## Contributing

Before opening a PR, answer one question:

> **Can this feature exist entirely outside `engine.rs`?**

If yes — it does not belong in the TCB. Extensions, adapters, and new modules are welcome. Changes that touch TCB files require a written justification and must pass seven CI guards (four on `engine.rs`, three on `capability.rs`).

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the full rules and [`TCB.md`](TCB.md) for the boundary definition.

---

## License

MIT. See [LICENSE](LICENSE).
