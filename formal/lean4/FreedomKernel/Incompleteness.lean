-- formal/lean4/FreedomKernel/Incompleteness.lean
-- Formal statement of what Freedom Kernel cannot prove.
-- This is a strength, not a weakness. seL4 documents the same gap.

namespace FreedomKernel.Incompleteness

-- ── Rice's Theorem (informal) ─────────────────────────────────────────────────

-- By Rice's theorem, no algorithm can decide whether an arbitrary
-- infinite sequence of PERMITTED actions reaches an unsafe state.

-- RESPONSE: verify_plan() operates on a bounded plan prefix of depth n.
-- GUARANTEE: no prefix of length ≤ n violates temporal invariants.
-- GAP: the range (n, ∞) is not covered.

-- Stated as an axiom (undecidability result):
axiom infinite_horizon_undecidable :
  ¬ ∃ (decide : List Unit → Bool),
    ∀ (plan : List Unit),
      decide plan = true ↔ True  -- placeholder for "all-safe predicate"

-- ── Semantic Intent ───────────────────────────────────────────────────────────

-- The kernel verifies typed predicates, not intent.
-- Action("read-research", bot, resources_read=[paper]) is PERMITTED
-- if bot has delegation — even if "research" is a pretext.
-- The kernel cannot distinguish genuine intent from pretext.

-- Stated as a non-theorem:
-- There is no formal proof that permitted actions are "genuinely safe"
-- in the semantic sense. Safety requires the ownership graph to accurately
-- reflect the human owner's actual intent.

-- ── Axiom Soundness ───────────────────────────────────────────────────────────

-- The kernel enforces A1–A7. Whether A1–A7 are the correct axioms is
-- a philosophical question outside the scope of formal verification.
-- The kernel is sound relative to A1–A7; it cannot verify A1–A7 themselves.

-- ── What IS formally proved ───────────────────────────────────────────────────

-- See TCB.lean for proved theorems:
-- P1: forbidden_flags_always_block   (unconditional, proved by simp)
-- P5: verify_deterministic           (proved by rfl)
-- P2: permitted_implies_no_forbidden_flag
-- Individual flag corollaries (sovereignty, coercion, deception)
-- Temporal taint monotonicity (Temporal.lean)
-- Attenuation cannot escalate (MultiAgent.lean)

end FreedomKernel.Incompleteness
