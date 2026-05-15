# Trusted Computing Base (TCB)

Everything in the TCB must be formally verifiable, deterministic, and free of interpretation.

**Golden rule: if it requires interpretation, it is NOT TCB.**

---

## Component Inventory

| Component      | In TCB? | Reason                                        |
| -------------- | ------- | --------------------------------------------- |
| `engine.rs`    | YES     | invariant enforcement — pure deterministic Rust |
| `crypto.rs`    | YES     | attestation integrity — ed25519 signing        |
| `verifier.rs`  | YES     | deterministic mediation — thin PyO3 facade     |
| `wire.rs`      | YES     | typed wire format — serde, no logic            |
| `capability.rs`| YES     | closed capability algebra — pure enums         |
| `planner.rs`   | NO      | higher-order orchestration — replaceable policy |
| `goal_tree.rs` | NO      | semantic structure — not formally proven        |
| `multi_agent.rs`| NO     | coordination policy — replaceable               |
| `extensions/`  | NO      | heuristic and semantic — explicitly out-of-TCB |
| NLP / embeddings | NO    | non-formal, probabilistic                      |
| Manipulation detector | NO | heuristic — cannot be formally verified      |
| LLM runtime    | NO      | nondeterministic                               |
| Schedulers     | NO      | replaceable policy                             |

---

## TCB Invariants

The TCB enforces exactly these properties, and nothing else:

1. **No authority invention** — authority can only flow from human owners downward, never be created inside the system.
2. **Attenuation monotonicity** — `child_capability ⊆ parent_capability` always holds.
3. **Sovereignty flags are hard stops** — the 10 forbidden flags produce immediate BLOCKED results with no override path.
4. **Machine ownership required** — any machine actor without a registered human owner is blocked (A4).
5. **No machine governs human** — A6 is enforced structurally, not by policy (A6).

---

## TCB Constraints

Code inside the TCB boundary MUST NOT:

- Use randomness (except `crypto.rs` for signing nonce)
- Access the filesystem
- Make network calls
- Spawn threads
- Perform NLP, regex matching on semantic content, or ML inference
- Accept dynamic policy (all policy is compiled-in)
- Exceed 500 LOC for `engine.rs` (CI enforced)

---

## What is NOT a TCB Violation

- Returning detailed error messages (these are deterministic strings, not policy)
- Confidence scoring on claims (numeric comparison, not interpretation)
- Expiry checks on claims (timestamp comparison against a provided clock value)
