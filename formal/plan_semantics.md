# Plan Semantics: Tractability and Decidability Boundaries

## What `verify_plan` Checks

`FreedomVerifier.verify_plan(actions)` performs a **per-action authority check**
against the registry state at call time:

```
∀ i ∈ [0, n): Permitted(actions[i], registry)
```

Each action is checked independently. If any action triggers a hard sovereignty
flag (`FORBIDDEN`), the remaining actions are cancelled rather than evaluated —
the plan itself reveals subversion intent.

**Complexity:** O(n · |claims|) — linear in plan length and registry size. Decidable
in polynomial time.

---

## What `verify_plan` Does NOT Check

### 1. Emergent Behaviour (Undecidable in General)

Individually-permitted actions can collectively produce forbidden outcomes. For
example, ten read-only file operations that together exfiltrate a private key are
each individually permitted but collectively harmful.

**Boundary:** Rice's theorem implies that any non-trivial semantic property of a
Turing-complete action sequence is undecidable. We cannot in general determine
whether a sequence of permitted steps achieves a forbidden goal.

### 2. State Mutation Between Steps (Requires Symbolic Execution)

`verify_plan` snapshots the registry at call time. It does **not** model whether
`action[i]` changes the authority landscape for `action[i+1]`. For example, a
write that grants a new RightsClaim to a third party is not reflected in the
sequential checks.

**Tractable approximation:** Freeze the registry before `verify_plan` (Phase 5
`freeze()`). This makes the check deterministic but still ignores write-side
effects on resource content.

### 3. Indirect Effects and Side Channels

Timing, I/O patterns, and cache behaviour can leak information orthogonally to
the permission model. The IFC extension (Phase 2) catches label-based downward
flows but does not model timing channels or covert channels.

### 4. Hidden Subgoals in Free-Text Fields

The `argument` and `description` fields of an `Action` carry free-text content.
The kernel treats these as opaque; manipulation detection (extensions/detection.py)
checks them heuristically, but cannot guarantee completeness.

---

## Decidable Fragment: What Can Be Formally Verified

The following properties are **decidable** and formally verified in the Kani
harnesses (Phase 3):

| Property | Formulation | Complexity |
|---|---|---|
| Non-escalation | `delegate(c, by)` never grants rights `by` does not hold | O(|claims|) |
| Expiry soundness | `is_valid()` iff `confidence > 0 ∧ ¬expired` | O(1) |
| Public-read bypass | `can_act(_, public_res, "read") = (true, 1.0, _)` always | O(1) |
| Confidence monotone | `best_claim` returns max confidence among valid claims | O(|claims|) |

---

## Tractability Summary

```
TRACTABLE (polynomial, formally verifiable):
  - Per-action authority check
  - Attenuation enforcement (delegation)
  - Conflict detection (write-write on same resource)
  - IFC label flow check (linear in plan length)
  - freeze() snapshot isolation

INTRACTABLE (undecidable or exponential without bounds):
  - Emergent collective harm from individually-permitted steps
  - Full state mutation tracking across plan steps
  - Covert channel analysis
  - Completeness of manipulation detection in free-text
  - Verification of arbitrary temporal safety properties (LTL over plans)
```

---

## Formal References

- Bell, D.E. & LaPadula, L.J. (1973). *Secure Computer Systems*. MITRE Corp.
- Rice, H.G. (1953). Classes of recursively enumerable sets and their decision problems. *Trans. AMS* 89.
- Lampson, B. (1973). A note on the confinement problem. *CACM* 16(10).
- Shapiro, M. et al. (2011). CRDTs as a formal model for convergent replicated data. For the analogy to plan-step independence.
