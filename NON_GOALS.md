# Non-Goals

This document exists to prevent scope explosion. Every item listed here is a real request
that has been explicitly rejected. If a proposed feature requires any of these capabilities,
it does not belong in this kernel.

---

## Freedom Kernel does NOT:

- **Solve alignment** — it enforces authority boundaries, not values
- **Infer intent** — all decisions are based on explicit, typed claims
- **Understand natural language** — no NLP enters the kernel or TCB
- **Detect truth** — claims are accepted as-presented; truth is the caller's responsibility
- **Guarantee benevolence** — a well-owned, correctly-authorized machine can still be misused
- **Prevent covert channels** — timing, steganography, and side-channels are out of scope
- **Contain superintelligence** — capability boundaries apply to actions, not thought
- **Verify semantic equivalence** — two actions with different text but same meaning are not unified
- **Score ethics** — there is no ethics score, alignment metric, or virtue measure
- **Replace alignment research** — this is infrastructure, not a solution to the hard problem
- **Operate without a human owner** — the system requires an explicit ownership graph
- **Enforce metaphysical claims** — A1 (divine ownership) is documented foundation, not runtime logic

---

## Why this matters

Projects fail when scope expands incrementally. Each non-goal above has been proposed
(internally or externally) as a natural extension. Each was rejected because it would
require semantic interpretation, probabilistic reasoning, or NLP — none of which can
be formally verified.

The kernel's value comes from what it *provably enforces*, not from what it claims to handle.

---

## The boundary test

Before adding any feature, ask:

> Does this feature require interpretation, probabilistic reasoning, NLP, or ML inference?

If yes → it does not belong in the kernel. It may belong in `extensions/`.
