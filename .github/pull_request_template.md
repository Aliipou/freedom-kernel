## What problem does this solve?
<!-- One sentence. -->

## Why this approach?
<!-- Why not simpler? What did you rule out? -->

---

## TCB Gate

**Answer this section if this PR touches `engine.rs`, `capability.rs`, `wire.rs`, or `crypto.rs`.
Skip if the change is entirely outside these files.**

### The constitutional question:

> Can this feature exist entirely outside `engine.rs`?

- [ ] I asked this question and the answer is **NO** — briefly explain why:

```
Reason this cannot live in extensions/, adapters/, or a new module:
[your answer here]
```

### TCB invariant checklist (engine.rs):

- [ ] This change adds **no interpretation** of semantic content
- [ ] This change adds **no NLP, regex-on-content, or heuristics**
- [ ] This change adds **no randomness, network, filesystem, or async**
- [ ] This change adds **no new public functions** (public API = `verify` only)
- [ ] This change adds **no new `use` imports** beyond `crate::capability` and `crate::wire`
- [ ] `engine.rs` LOC after this PR: ______ (must be ≤ 300)

If any of the above cannot be checked, **do not open this PR against engine.rs**.
Move the feature to `extensions/` or a new module outside the TCB.

---

## General checklist

**Design**
- [ ] Can this code be deleted later without surgery?
- [ ] Is naming self-explanatory without a comment?
- [ ] Can you explain the failure mode in one sentence?

**Quality**
- [ ] Every new test verifies a real behavior, not just coverage
- [ ] No new `unwrap()` / `expect()` in TCB files (clippy enforces this)

**If AI-assisted**
- [ ] You read and understood every line before submitting
- [ ] No auth/security/TCB code was taken from AI output without full review
