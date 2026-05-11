# Threat Model

This kernel provides formal capability-security boundaries for autonomous agent execution.
Without an explicit threat model, formal verification is cosmetic.

---

## Trusted

The following are assumed correct and are not defended against:

| Component                | Trust basis                                      |
| ------------------------ | ------------------------------------------------ |
| `verifier.rs` + `engine.rs` | Formally specified; subject to mechanical proof |
| Cryptographic primitives | `ed25519-dalek`, `rand_core` — audited crates   |
| Registry integrity       | Caller is responsible for registry construction  |
| Rust compiler + stdlib   | Trusted toolchain assumption                     |
| Hardware RNG (`OsRng`)   | Required for signing nonce generation            |

---

## Untrusted

The following are explicitly untrusted and handled by the kernel's enforcement:

| Component         | Threat                                              |
| ----------------- | --------------------------------------------------- |
| LLMs              | May produce arbitrary action requests; must be verified |
| Humans            | May construct malformed registries or forge claims  |
| Prompts           | Semantic content is not trusted; only typed claims count |
| Schedulers        | May submit actions out-of-order or replay old ones  |
| Tools             | External tools are untrusted callers of the kernel  |
| IPC payloads      | May be malformed, replayed, or crafted              |
| Embeddings        | Semantic vectors — not formally verifiable          |
| Plugin extensions | `extensions/` code is explicitly outside the TCB   |

---

## Attack Surface

### In scope (defended)

- **Privilege escalation via delegation** — attenuation semantics prevent this; `child ⊆ parent` is enforced
- **Ownerless machine acting** — A4 check blocks any machine without a registered human owner
- **Machine governing human** — A6 check is a hard structural block
- **Sovereignty flag bypass** — 10 flags produce immediate BLOCKED with no override
- **Replay attacks** — signatures include timestamp + 16-byte random nonce
- **Confidence inflation** — delegated confidence cannot exceed delegator's confidence
- **Recursive delegation explosion** — `ExecutionContext` enforces a hard depth limit

### Out of scope (not defended)

- **Side-channel attacks** — timing leakage, cache timing, power analysis
- **Timing leakage** — the verifier does not attempt constant-time claim lookup
- **Steganography** — covert channels in data content are not detectable
- **Compromised kernel host** — if the OS or hardware is compromised, guarantees do not hold
- **Malicious owners** — a legitimate human owner who acts maliciously is not constrained
- **Supply-chain attacks** — compiler, crate, or toolchain compromise is out of scope
- **Semantic covert channels** — an LLM that encodes information in its output text is not detected

---

## Security Properties Claimed

1. **Confinement** — an agent cannot act on resources for which it holds no valid claim
2. **Non-fabrication** — agents cannot create authority that does not flow from a human owner
3. **Attenuation** — delegated authority is always a strict subset of the delegator's authority
4. **Sovereignty hard stops** — the 10 forbidden flags cannot be circumvented from within the system
5. **Cryptographic attestation** — every decision is signed with ed25519; verifiable by any holder of the public key

## Security Properties NOT Claimed

- Semantic correctness of actions (the kernel verifies authority, not intent)
- Absence of covert channels
- Protection against compromised infrastructure
- Guaranteed termination under adversarial input (bounded by Rust's type system, not proven)
