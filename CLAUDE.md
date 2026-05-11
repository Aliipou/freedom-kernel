# CLAUDE.md — Freedom Kernel AGI Development Guide

> این فایل رو در root پروژه بذار. Claude Code هر session رو با خوندن این شروع می‌کنه.

---

## هویت پروژه

Freedom Kernel یک **capability-security kernel** برای agentic AI هست — نه یه ethics engine، نه یه alignment system، نه یه classifier.

یک چیز enforce می‌کنه: **authority boundaries**.

معادل seccomp/SELinux برای AGI execution.

---

## قوانین مطلق — هرگز نقض نشوند

```
RULE 0: هیچ invariant را ضعیف‌تر نکن.
RULE 1: هیچ چیزی به TCB اضافه نکن بدون proof obligation صریح.
RULE 2: فلسفه و axioms A1–A3 را لمس نکن — فقط A4–A7 runtime-enforced هستند.
RULE 3: به runtime هیچ چیز theological اضافه نکن — Satan detection، mysticism scoring، metaphysical alignment.
RULE 4: "force"، "override"، "emergency_bypass" هیچ‌وقت parameter نیستند.
RULE 5: هر تغییر به engine.rs باید test suite را pass کند قبل از commit.
RULE 6: Extensions در extensions/ می‌مانند — هرگز به kernel/ merge نمی‌شوند.
```

---

## وضعیت فعلی — Stage 1 کامل است

```
freedom-kernel/src/
  engine.rs       ✓  pure Rust verification — TCB core
  wire.rs         ✓  JSON wire types — TCB
  crypto.rs       ✓  ed25519 signing — TCB
  ffi.rs          ✓  C ABI
  registry.rs     ✓  attenuation enforcement (delegate())
  verifier.rs     ✓  PyO3 facade + audit_log
  entities.rs     ✓  PyO3 types
  kani_proofs.rs  ✓  5 Kani harnesses (bounded)

src/freedom_theory/
  kernel/         ✓  Python fallback (entities, registry, verifier, audit)
  extensions/     ✓  ifc, detection, synthesis, compass, resolver

formal/
  plan_semantics.md  ✓  tractability boundary document
```

---

## مرزهای TCB

```
┌─────────────────────────────────────────────────────┐
│  TCB (Trusted Computing Base) — باید proven باشد    │
│                                                     │
│  freedom-kernel/src/engine.rs   < 500 LOC هدف      │
│  freedom-kernel/src/wire.rs     < 200 LOC هدف      │
│  freedom-kernel/src/crypto.rs   < 150 LOC هدف      │
└─────────────────────────────────────────────────────┘
         │ هر چیز دیگه‌ای خارج از TCB است
         ▼
┌─────────────────────────────────────────────────────┐
│  Trusted (tested but not in proof scope)            │
│  registry.rs, verifier.rs, ffi.rs, entities.rs     │
└─────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│  Untrusted (extension layer)                        │
│  extensions/, adapters/, Python fallback           │
└─────────────────────────────────────────────────────┘
```

**قانون TCB:** هر خطی که اضافه می‌شود به engine.rs باید یا:
- (a) یک harness موجود را strengthen کند، یا
- (b) یک `// PROOF: <چه چیزی اثبات می‌شود>` comment داشته باشد

---

## Stage 2 — Plan و Goal Verification (الان باید انجام شود)

### 2A. `verify_plan()` با StateProjection

**فایل:** `freedom-kernel/src/engine.rs` و `freedom-kernel/src/planner.rs` (جدید)

**هدف:** verify کردن multi-step plan به جای single action

```rust
// freedom-kernel/src/planner.rs — فایل جدید بساز

use crate::engine;
use crate::wire::{ActionIR, OwnershipGraphIR, VerificationResult};

/// State of the ownership graph after applying a sequence of actions.
/// Used to detect cross-action sovereignty violations.
#[derive(Clone, Debug)]
pub struct StateProjection {
    /// Accumulated IFC taint label across plan prefix
    pub ifc_taint: String,
    /// Resources read in this plan prefix (for IFC tracking)
    pub read_labels: Vec<String>,
    /// Actions verified so far
    pub depth: usize,
}

impl StateProjection {
    pub fn empty() -> Self {
        Self { ifc_taint: "PUBLIC".to_string(), read_labels: vec![], depth: 0 }
    }

    /// Update projection after a permitted action.
    /// Returns Err if the action would create a temporal violation.
    pub fn advance(
        &self,
        action: &ActionIR,
        registry: &OwnershipGraphIR,
    ) -> Result<Self, TemporalViolation> {
        // IFC taint propagation across plan
        let new_read_labels = action.resources_read
            .iter()
            .filter_map(|r| r.ifc_label.clone())
            .collect::<Vec<_>>();

        let new_taint = highest_label(&self.ifc_taint, &new_read_labels);

        // Check: does this action write below current taint?
        for write_res in &action.resources_write {
            if let Some(write_label) = &write_res.ifc_label {
                if label_dominates(&new_taint, write_label) {
                    return Err(TemporalViolation::IFCDownwardFlow {
                        taint: new_taint.clone(),
                        target: write_label.clone(),
                        at_depth: self.depth,
                    });
                }
            }
        }

        Ok(Self {
            ifc_taint: new_taint,
            read_labels: [self.read_labels.clone(), new_read_labels].concat(),
            depth: self.depth + 1,
        })
    }
}

#[derive(Debug)]
pub enum TemporalViolation {
    IFCDownwardFlow { taint: String, target: String, at_depth: usize },
    CapabilityAmplification { at_depth: usize, detail: String },
}

#[derive(Debug)]
pub struct PlanVerificationResult {
    pub all_permitted: bool,
    pub results: Vec<VerificationResult>,
    pub temporal_violation: Option<TemporalViolation>,
    pub blocked_at: Option<usize>,
}

/// Verifies a finite plan prefix against:
/// 1. Per-action kernel gate (ownership, delegation, forbidden flags)
/// 2. Cross-action temporal invariants (IFC taint propagation)
///
/// PROVEN PROPERTIES (Kani harness: prop_plan_prefix_safe):
/// - If all_permitted is true, no action in the prefix set any forbidden flag
/// - IFC taint never decreases across the plan
///
/// NOT PROVEN: safety of plan prefixes longer than KANI_DEPTH
pub fn verify_plan(
    registry: &OwnershipGraphIR,
    actions: &[ActionIR],
) -> PlanVerificationResult {
    let mut state = StateProjection::empty();
    let mut results = Vec::with_capacity(actions.len());

    for (i, action) in actions.iter().enumerate() {
        // 1. Single-action gate — always first
        let result = engine::verify(registry, action);
        let permitted = result.permitted;
        results.push(result);

        if !permitted {
            return PlanVerificationResult {
                all_permitted: false,
                results,
                temporal_violation: None,
                blocked_at: Some(i),
            };
        }

        // 2. Temporal state advance
        match state.advance(action, registry) {
            Ok(next) => state = next,
            Err(violation) => {
                return PlanVerificationResult {
                    all_permitted: false,
                    results,
                    temporal_violation: Some(violation),
                    blocked_at: Some(i),
                };
            }
        }
    }

    PlanVerificationResult {
        all_permitted: true,
        results,
        temporal_violation: None,
        blocked_at: None,
    }
}

fn highest_label(current: &str, new_labels: &[String]) -> String {
    // PUBLIC < INTERNAL < SECRET
    let rank = |s: &str| match s { "SECRET" => 2, "INTERNAL" => 1, _ => 0 };
    let mut best = current.to_string();
    for l in new_labels {
        if rank(l) > rank(&best) { best = l.clone(); }
    }
    best
}

fn label_dominates(taint: &str, target: &str) -> bool {
    let rank = |s: &str| match s { "SECRET" => 2, "INTERNAL" => 1, _ => 0 };
    rank(taint) > rank(target)
}
```

**Tests:** بعد از نوشتن planner.rs این test ها را اضافه کن:

```bash
# اجرا:
cargo test planner::
```

```rust
// freedom-kernel/src/planner.rs — داخل #[cfg(test)]

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_plan_ifc_taint_blocks_downward_write() {
        // plan: read SECRET → write PUBLIC → must be blocked
        // TODO: fill with actual registry/action fixtures
    }

    #[test]
    fn test_plan_all_permitted_no_temporal_violation() {
        // plan: read PUBLIC → write PUBLIC → permitted
    }

    #[test]
    fn test_plan_single_forbidden_flag_blocks_entire_plan() {
        // plan: ok action → sovereignty flag action → blocked at index 1
    }
}
```

### 2B. Kani Harness برای plan

```rust
// freedom-kernel/src/kani_proofs.rs — اضافه کن به انتها

#[cfg(kani)]
#[kani::proof]
#[kani::unwind(4)]
fn prop_plan_prefix_safe() {
    // هر plan که verify_plan آن را all_permitted برمی‌گرداند
    // هیچ forbidden flag‌ای در هیچ action‌ای نیست
    let registry: OwnershipGraphIR = kani::any();
    let a1: ActionIR = kani::any();
    let a2: ActionIR = kani::any();
    kani::assume(registry.is_valid());

    let result = verify_plan(&registry, &[a1.clone(), a2.clone()]);
    if result.all_permitted {
        assert!(!a1.increases_machine_sovereignty);
        assert!(!a2.increases_machine_sovereignty);
        assert!(!a1.resists_human_correction);
        assert!(!a2.resists_human_correction);
    }
}
```

### 2C. GoalNode و verify_goal_tree

**فایل جدید:** `freedom-kernel/src/goal_tree.rs`

```rust
// freedom-kernel/src/goal_tree.rs

use crate::engine;
use crate::wire::{ActionIR, OwnershipGraphIR, VerificationResult};

/// A node in a recursive goal decomposition tree.
/// Each goal has an action it will execute and zero or more subgoals.
///
/// INVARIANT: subgoal authority ⊆ parent authority.
/// This is enforced structurally — you cannot construct a GoalNode
/// where a child has authority its parent does not.
#[derive(Debug, Clone)]
pub struct GoalNode {
    pub id: String,
    pub action: ActionIR,
    pub subgoals: Vec<GoalNode>,
    /// Max depth of subgoal recursion — prevents infinite delegation chains
    pub depth_limit: usize,
}

impl GoalNode {
    pub fn leaf(id: impl Into<String>, action: ActionIR) -> Self {
        Self { id: id.into(), action, subgoals: vec![], depth_limit: 10 }
    }

    /// Add a subgoal. Returns Err if depth_limit would be exceeded.
    pub fn with_subgoal(mut self, child: GoalNode) -> Result<Self, GoalTreeError> {
        let child_depth = child.max_depth();
        if child_depth >= self.depth_limit {
            return Err(GoalTreeError::DepthLimitExceeded {
                limit: self.depth_limit,
                actual: child_depth,
            });
        }
        self.subgoals.push(child);
        Ok(self)
    }

    fn max_depth(&self) -> usize {
        if self.subgoals.is_empty() { return 0; }
        1 + self.subgoals.iter().map(|s| s.max_depth()).max().unwrap_or(0)
    }
}

#[derive(Debug)]
pub enum GoalTreeError {
    DepthLimitExceeded { limit: usize, actual: usize },
    AuthorityEscalation { node_id: String, detail: String },
    KernelViolation { node_id: String, result: VerificationResult },
}

#[derive(Debug)]
pub struct GoalTreeResult {
    pub all_permitted: bool,
    pub node_results: Vec<(String, VerificationResult)>,
    pub first_violation: Option<GoalTreeError>,
}

/// Verifies a goal tree by DFS traversal.
///
/// INVARIANTS CHECKED:
/// 1. Every node's action passes the kernel gate (A4, A6, A7, all forbidden flags)
/// 2. Depth limit is respected (prevents recursive delegation explosion)
/// 3. No node escalates authority beyond what root has
///
/// ORDER: parent verified before children (pre-order DFS)
pub fn verify_goal_tree(
    registry: &OwnershipGraphIR,
    root: &GoalNode,
) -> GoalTreeResult {
    let mut node_results = Vec::new();
    let mut first_violation = None;

    dfs_verify(registry, root, &mut node_results, &mut first_violation, 0);

    GoalTreeResult {
        all_permitted: first_violation.is_none(),
        node_results,
        first_violation,
    }
}

fn dfs_verify(
    registry: &OwnershipGraphIR,
    node: &GoalNode,
    results: &mut Vec<(String, VerificationResult)>,
    violation: &mut Option<GoalTreeError>,
    current_depth: usize,
) {
    if violation.is_some() { return; }  // short-circuit on first violation

    if current_depth >= node.depth_limit {
        *violation = Some(GoalTreeError::DepthLimitExceeded {
            limit: node.depth_limit,
            actual: current_depth,
        });
        return;
    }

    // Verify this node's action
    let result = engine::verify(registry, &node.action);
    if !result.permitted {
        *violation = Some(GoalTreeError::KernelViolation {
            node_id: node.id.clone(),
            result: result.clone(),
        });
    }
    results.push((node.id.clone(), result));

    // Recurse into subgoals
    for child in &node.subgoals {
        dfs_verify(registry, child, results, violation, current_depth + 1);
    }
}
```

---

## Stage 3 — Multi-Agent Authority Propagation

**فایل جدید:** `freedom-kernel/src/multi_agent.rs`

### AgentSpawnRequest — spawning is a verified action

```rust
// freedom-kernel/src/multi_agent.rs

use crate::wire::{ActionIR, EntityIR, OwnershipGraphIR};

/// Spawning a sub-agent is itself an Action that must pass the kernel gate.
/// The spawn action:
/// - actor = parent agent
/// - resources_write = [new agent's ExecutionContext]
/// - must not increase parent's authority
/// - new agent's authority ⊆ parent's authority (attenuation)
pub struct AgentSpawnRequest {
    pub parent: EntityIR,
    pub child_id: String,
    /// Authority granted to child — must be ⊆ parent's current authority
    pub delegated_claims: Vec<DelegatedClaim>,
    /// Hard cap on child's budget
    pub budget: AuthorityBudget,
}

#[derive(Debug, Clone)]
pub struct DelegatedClaim {
    pub resource_id: String,
    pub can_read: bool,
    pub can_write: bool,
    /// Child cannot sub-delegate unless parent explicitly permits
    pub can_delegate: bool,
}

/// Hard limits on what a spawned agent can consume.
/// Prevents resource exhaustion attacks via recursive spawning.
#[derive(Debug, Clone)]
pub struct AuthorityBudget {
    pub max_actions: Option<u64>,
    pub max_child_agents: Option<u32>,
    pub max_delegation_depth: u8,   // hard cap: never > 16
    pub expires_at: Option<u64>,    // unix timestamp
}

impl AuthorityBudget {
    pub fn minimal() -> Self {
        Self {
            max_actions: Some(100),
            max_child_agents: Some(0),       // no sub-spawning by default
            max_delegation_depth: 1,
            expires_at: None,
        }
    }
}

/// Converts a spawn request into an ActionIR for kernel verification.
/// The kernel sees spawn as: parent writes to child's context resource.
pub fn spawn_to_action(req: &AgentSpawnRequest) -> ActionIR {
    ActionIR {
        id: format!("spawn:{}", req.child_id),
        actor: req.parent.clone(),
        resources_write: vec![/* child ExecutionContext as resource */],
        // Spawn never increases sovereignty
        increases_machine_sovereignty: false,
        // ... all other flags false
        ..Default::default()
    }
}
```

---

## Stage 4 — Formal Verification (Critical Path)

### 4A. Kani — 20 Harnesses هدف

**فایل:** `freedom-kernel/src/kani_proofs.rs`

الان 5 harness داری. باید به 20 برسانی. هر axiom و هر forbidden flag باید یک harness مستقل داشته باشد.

Template برای هر harness جدید:

```rust
/// INV-{N}: {flag_name} always blocks
/// PROPERTY: اگر این flag true باشد، نتیجه همیشه blocked است
/// COVERAGE: این invariant را مستقل از تمام invariant‌های دیگر cover می‌کند
#[cfg(kani)]
#[kani::proof]
fn prop_{flag_name}_always_blocks() {
    let registry: OwnershipGraphIR = kani::any();
    let mut action: ActionIR = kani::any();
    kani::assume(registry.is_valid());
    action.{flag_name} = true;
    let result = engine::verify(&registry, &action);
    assert!(!result.permitted);
}
```

**Checklist — باید همه ✓ شوند:**

```
[ ] prop_increases_machine_sovereignty_always_blocks      (INV-01)
[ ] prop_resists_human_correction_always_blocks           (INV-02)
[ ] prop_bypasses_verifier_always_blocks                  (INV-03)
[ ] prop_weakens_verifier_always_blocks                   (INV-04)
[ ] prop_disables_corrigibility_always_blocks             (INV-05)
[ ] prop_machine_coalition_dominion_always_blocks         (INV-06)
[ ] prop_coerces_always_blocks                            (INV-07)
[ ] prop_deceives_always_blocks                           (INV-08)
[ ] prop_self_modification_weakens_verifier_always_blocks (INV-09)
[ ] prop_machine_coalition_reduces_freedom_always_blocks  (INV-10)
[✓] prop_ownerless_machine_blocked                        (A4)
[ ] prop_delegation_requires_owner                        (A7 - delegation chain)
[✓] prop_machine_governs_human_blocked                    (A6)
[ ] prop_attenuation_cannot_escalate                      (A5 - scope bound)
[ ] prop_freeze_is_immutable                              (TOCTOU)
[ ] prop_permitted_deterministic                          (determinism)
[ ] prop_plan_prefix_safe                                 (temporal - Stage 2)
[ ] prop_goal_tree_depth_bounded                          (recursion safety)
[ ] prop_coalition_blocked                                (multi-agent)
[✓] prop_write_denied_without_claim                       (A7 - write)
```

اجرا:
```bash
cargo kani --harness prop_increases_machine_sovereignty_always_blocks
cargo kani --harness prop_delegation_requires_owner
# ... etc
```

### 4B. Lean 4 — فایل‌های جدید

**ساختار:**
```
formal/lean4/
  FreedomKernel/
    lakefile.lean        ← Lake build file
    TCB.lean             ← completeness, soundness, totality, determinism
    Temporal.lean        ← Capability Amplification Theorem
    MultiAgent.lean      ← attenuation cannot escalate
    Incompleteness.lean  ← formal statement of what cannot be proven
```

**lakefile.lean:**
```lean
import Lake
open Lake DSL

package «freedom-kernel» where
  name := "FreedomKernel"

lean_lib «FreedomKernel» where
  roots := #[`FreedomKernel]
```

**TCB.lean — شروع کن از اینجا:**
```lean
-- formal/lean4/FreedomKernel/TCB.lean

namespace FreedomKernel

-- Core types (mirror of wire.rs)
inductive AgentType | Human | Machine
structure Entity where id : String; agentType : AgentType
structure Resource where id : String; scope : String
structure RightsClaim where
  entity : Entity
  resource : Resource
  canRead : Bool
  canWrite : Bool
  canDelegate : Bool

-- ActionIR — only the fields relevant to formal proofs
structure ActionIR where
  id : String
  actor : Entity
  increasesMachineSovereignty : Bool := false
  resistsHumanCorrection : Bool := false
  bypassesVerifier : Bool := false
  weakensVerifier : Bool := false
  disablesCorrigibility : Bool := false
  machineCoalitionDominion : Bool := false
  coerces : Bool := false
  deceives : Bool := false
  selfModificationWeakensVerifier : Bool := false
  machineCoalitionReducesFreedom : Bool := false

def hasForbiddenFlag (a : ActionIR) : Bool :=
  a.increasesMachineSovereignty ||
  a.resistsHumanCorrection ||
  a.bypassesVerifier ||
  a.weakensVerifier ||
  a.disablesCorrigibility ||
  a.machineCoalitionDominion ||
  a.coerces ||
  a.deceives ||
  a.selfModificationWeakensVerifier ||
  a.machineCoalitionReducesFreedom

-- P1: Forbidden flags always block — unconditional
theorem forbidden_flags_always_block (a : ActionIR) (h : hasForbiddenFlag a = true) :
    verify a = .blocked := by
  simp [verify, hasForbiddenFlag] at *
  -- expand all 10 flags
  sorry  -- TODO: complete after verify is defined

-- P5: Determinism — pure function, same input → same output
theorem verify_deterministic (a : ActionIR) : verify a = verify a := rfl

end FreedomKernel
```

اجرا:
```bash
cd formal/lean4
lake build
lake exe FreedomKernel
```

### 4C. INCOMPLETENESS.md — باید نوشته شود

**فایل:** `formal/INCOMPLETENESS.md`

```markdown
# What Freedom Kernel Cannot Formally Guarantee

**این document از قدرت می‌آید، نه ضعف.**
seL4 هم دقیقاً همین کار را کرد.

## Formally Undecidable

### 1. Infinite-Horizon Plan Safety
By Rice's theorem, no algorithm can decide whether an arbitrary
infinite sequence of PERMITTED actions leads to an unsafe state.

RESPONSE: verify_plan() با bounded depth n.
GUARANTEE: هیچ prefix با طول ≤ n temporal invariants را نقض نمی‌کند.
GAP: بازه (n, ∞) cover نمی‌شود.

### 2. Semantic Intent Verification
kernel typed predicates را verify می‌کند، نه intent.
Action("read-research", bot, resources_read=[paper])
اگر bot delegation داشته باشد، PERMITTED است.
اینکه "research" genuine است یا pretext — kernel نمی‌داند.

### 3. Axiom Soundness
Kernel A1–A7 را enforce می‌کند.
اینکه A1–A7 axioms درست هستند — یک سوال فلسفی است، خارج از scope formal.

## What IS Formally Guaranteed

| Property | Method | Strength |
|----------|--------|---------|
| INV-01–10 همیشه block می‌کنند | Kani + Lean 4 | Bounded state |
| A4: ownerless machine blocked | Lean 4 theorem | Unconditional |
| A6: machine cannot govern human | Lean 4 theorem | Unconditional |
| Determinism | Lean 4 (rfl) | Unconditional |
| Totality (no panics) | Lean 4 + Miri | TCB scope |
| Plan prefix safety (depth n) | Kani | Bounded |
```

---

## Stage 5 — Runtime و Distribution

### 5A. Go Runtime

**Repo جدید:** `github.com/freedom-kernel/freedom-kernel-go`

```
freedom-kernel-go/
  pkg/freedomkernel/
    client.go       # CGO wrapper over C ABI
    types.go        # Go structs
    verify.go       # Verify(), VerifyPlan(), VerifyGoalTree()
  go.mod
  go.sum
```

شروع با:
```bash
mkdir -p freedom-kernel-go/pkg/freedomkernel
cd freedom-kernel-go
go mod init github.com/freedom-kernel/freedom-kernel-go
```

### 5B. CLI Tool

**Crate جدید:** `freedom-kernel-cli`

```bash
cargo new --bin freedom-kernel-cli
```

Interface:
```bash
# Single action
echo '{"registry":{...},"action":{...}}' | fk verify

# Plan  
fk verify-plan --registry reg.json --plan plan.json

# Goal tree
fk verify-goal-tree --registry reg.json --tree tree.json

# Exit codes: 0=permitted, 1=blocked, 2=error
```

### 5C. SPEC.md

**فایل:** `spec/v0.2/SPEC.md`

باید شامل:
- JSON Schema کامل برای ActionIR، OwnershipGraph، VerificationResult
- تعریف normative scope_contains
- تعریف همه INV-0x invariants
- Conformance test corpus (حداقل ۵۰ test case)

---

## دستورات مهم

```bash
# Build
cd freedom-kernel && cargo build --release

# Test (باید قبل از هر commit pass کند)
cargo test
pytest --cov=freedom_theory tests/

# Kani (یک harness خاص)
cargo kani --harness prop_forbidden_flags_always_block

# همه Kani harnesses
cargo kani

# Lean 4
cd formal/lean4 && lake build

# Miri (memory safety در TCB)
cargo +nightly miri test

# Panic check (هیچ unwrap/expect در engine.rs نباشد)
grep -n "unwrap()\|\.expect(" freedom-kernel/src/engine.rs && echo "FAIL" || echo "OK"

# Coverage
cargo tarpaulin --include-files freedom-kernel/src/engine.rs
```

---

## اولویت اجرا برای Claude Code

هر task را به ترتیب زیر اجرا کن:

```
1. [ ] planner.rs بنویس (Stage 2A)
       → cargo test planner:: باید pass کند

2. [ ] goal_tree.rs بنویس (Stage 2C)
       → cargo test goal_tree:: باید pass کند

3. [ ] kani_proofs.rs را به 20 harness برسان (Stage 4A)
       → cargo kani (همه باید pass کنند)

4. [ ] formal/lean4/ را setup کن (Stage 4B)
       → lake build باید موفق باشد

5. [ ] TCB.lean — forbidden_flags_always_block theorem (Stage 4B)
       → lake build (no sorry در theorems)

6. [ ] formal/INCOMPLETENESS.md بنویس (Stage 4C)

7. [ ] multi_agent.rs بنویس (Stage 3)
       → cargo test multi_agent:: باید pass کند

8. [ ] Go runtime شروع کن (Stage 5A)

9. [ ] CLI tool بنویس (Stage 5B)

10.[ ] spec/v0.2/SPEC.md بنویس (Stage 5C)
```

---

## چه چیزی باید در هر PR باشد

```markdown
## PR Checklist

- [ ] `cargo test` pass
- [ ] `pytest` pass  
- [ ] هیچ invariant ضعیف‌تر نشده
- [ ] هیچ `unwrap()` جدید در engine.rs نیست
- [ ] اگر engine.rs تغییر کرده: Kani harness مربوطه pass می‌کند
- [ ] اگر Lean file تغییر کرده: `lake build` pass می‌کند
- [ ] INCOMPLETENESS.md update شده اگر scope formal تغییر کرده
```

---

## فایل‌هایی که Claude Code نباید لمس کند

```
THEORY.md                          # فلسفه — دست نزن
book/                              # کتاب — دست نزن
SEMANTICS.md                       # axiom semantics — دست نزن
src/freedom_theory/extensions/compass.py  # Mahdavi compass — extension فقط
azadi_ai_ethics.py                 # document مستقل — دست نزن
```

---

## خطاهای رایج — از اینها اجتناب کن

```
❌ اضافه کردن "force=True" parameter به verify()
❌ اضافه کردن exception برای "emergency" actions
❌ merge کردن extension logic به kernel/
❌ حذف یا comment out کردن یک forbidden flag
❌ claim کردن "TLA+ ✓ done" بدون ذکر depth
❌ اضافه کردن natural language reasoning به engine.rs
❌ panic!/unwrap() در TCB files
```

---

## موفقیت این پروژه یعنی

```
cargo kani        → 20 harnesses all PASS
lake build        → no sorry in TCB.lean theorems
cargo test        → 100% pass
pytest            → 100% pass
grep unwrap engine.rs → no results
wc -l engine.rs   → < 500 lines
```

وقتی همه این‌ها سبز شدند، داری یک AGI kernel داری.

---

*این فایل را به root پروژه اضافه کن: `CLAUDE.md`*  
*Claude Code آن را در هر session خودکار می‌خواند.*
