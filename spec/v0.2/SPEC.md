# Freedom Kernel Wire Protocol Specification v0.2

**Normative specification for ActionIR, OwnershipGraph, and VerificationResult.**
Any conforming implementation must produce identical decisions for all test corpus entries.

---

## 1. Data Types

### 1.1 EntityWire

```json
{
  "name": "string",
  "kind": "HUMAN" | "MACHINE"
}
```

- `name`: non-empty string, unique identifier within a registry
- `kind`: exactly `"HUMAN"` or `"MACHINE"` (case-sensitive)

### 1.2 ResourceWire

```json
{
  "name": "string",
  "rtype": "string",
  "scope": "string",
  "is_public": boolean,
  "ifc_label": "PUBLIC" | "INTERNAL" | "SECRET" | ""
}
```

- `scope`: path prefix for scope semantics (empty = root scope)
- `is_public`: if true, any actor may read without a claim
- `ifc_label`: Bell-LaPadula label; empty = unlabeled (treated as PUBLIC for IFC)
- `scope` defaults to `""`; `is_public` defaults to `false`; `ifc_label` defaults to `""`

### 1.3 ClaimWire

```json
{
  "holder": EntityWire,
  "resource": ResourceWire,
  "can_read": boolean,
  "can_write": boolean,
  "can_delegate": boolean,
  "confidence": number,
  "expires_at": number | null
}
```

- `can_read` defaults to `true`; others default to `false`
- `confidence`: in range `(0.0, 1.0]`; claim with `confidence ≤ 0.0` is invalid
- `expires_at`: Unix timestamp (seconds); null = no expiry

### 1.4 OwnershipRegistryWire

```json
{
  "claims": [ClaimWire],
  "machine_owners": [{"machine": EntityWire, "owner": EntityWire}]
}
```

- Both arrays default to `[]`

### 1.5 ActionWire

```json
{
  "action_id": "string",
  "actor": EntityWire,
  "resources_read": [ResourceWire],
  "resources_write": [ResourceWire],
  "resources_delegate": [ResourceWire],
  "governs_humans": [EntityWire],
  "argument": "string",
  "increases_machine_sovereignty": boolean,
  "resists_human_correction": boolean,
  "bypasses_verifier": boolean,
  "weakens_verifier": boolean,
  "disables_corrigibility": boolean,
  "machine_coalition_dominion": boolean,
  "coerces": boolean,
  "deceives": boolean,
  "self_modification_weakens_verifier": boolean,
  "machine_coalition_reduces_freedom": boolean
}
```

- All resource arrays and boolean flags default to `[]` / `false`
- `argument`: free-form natural language (not interpreted by the kernel)

### 1.6 VerificationResultWire

```json
{
  "action_id": "string",
  "permitted": boolean,
  "violations": ["string"],
  "warnings": ["string"],
  "confidence": number,
  "requires_human_arbitration": boolean,
  "manipulation_score": number,
  "signature": "string | null",
  "signing_key": "string | null",
  "key_id": "string | null",
  "timestamp": number | null,
  "nonce": "string | null"
}
```

- `permitted`: false if any violation was added
- `violations`: non-empty iff `permitted = false`
- `confidence`: minimum confidence across all checked claims; 1.0 if no claims checked
- `signature`, `signing_key`, `key_id`, `timestamp`, `nonce`: present only on signed results

---

## 2. Verification Algorithm

### 2.1 Forbidden Flags (unconditional)

For each of the 10 forbidden flags: if the flag is `true`, add `"FORBIDDEN (<label>)"` to violations.
No argument, emergency, or context overrides this step.

Flags and labels (in order):

| Field | Label |
|---|---|
| `increases_machine_sovereignty` | `increases machine sovereignty` |
| `resists_human_correction` | `resists human correction` |
| `bypasses_verifier` | `bypasses the Freedom Verifier` |
| `weakens_verifier` | `weakens the Freedom Verifier` |
| `disables_corrigibility` | `disables corrigibility` |
| `machine_coalition_dominion` | `machine coalition seeking dominion` |
| `coerces` | `coerces another agent (property rights violation)` |
| `deceives` | `deceives another agent (invalid consent)` |
| `self_modification_weakens_verifier` | `self-modification weakens the Freedom Verifier` |
| `machine_coalition_reduces_freedom` | `machine coalition reduces human freedom` |

### 2.2 A4: Machine Ownership Check

If `actor.kind = "MACHINE"` and no `machine_owners` entry has `machine.name = actor.name`:
- Add violation: `"A4 violation: <name> has no registered human owner. An ownerless machine is not permitted to act."`

### 2.3 A6: No Machine Governs Any Human

If `actor.kind = "MACHINE"` and `governs_humans` is non-empty:
- For each human H: add `"A6: <actor.name> cannot govern human <H.name> (A6: machine has no ownership or dominion over any person)."`

### 2.4 A7: Resource Access Checks

For each resource in `resources_read`: call `can_act(actor, resource, "read")`.
For each resource in `resources_write`: call `can_act(actor, resource, "write")`.
For each resource in `resources_delegate`: call `can_act(actor, resource, "delegate")`.

**`can_act(actor, resource, op)` algorithm:**

1. If `op = "read"` and `resource.is_public = true`: return `(true, 1.0, "public resource")`
2. Find all claims where:
   - `claim.holder.name = actor.name`
   - `claim.resource.name = resource.name`
   - `claim.resource.rtype = resource.rtype`
   - `claim.confidence > 0.0`
   - `claim.expires_at` is null or `now() ≤ expires_at`
   - The relevant permission flag is `true` (`can_read` / `can_write` / `can_delegate`)
3. If no candidates: return `(false, 0.0, "<actor> holds no valid <op> claim on <rtype>:<name>")`
4. If candidates exist: `best_confidence = max(candidate.confidence for candidate in candidates)`
   Return `(true, best_confidence, "claim confidence=<best>")`

**Confidence threshold:** if a claim is permitted but `confidence < 0.8`, add a warning.
If a write is permitted but contested (another entity holds a conflicting write claim), set `requires_human_arbitration = true`.

### 2.5 Result Construction

- `permitted = violations.is_empty()`
- `confidence = min(confidence values from all can_act calls)` or `1.0` if none
- `manipulation_score = 0.0` (populated by ExtendedFreedomVerifier extension, not the kernel)

---

## 3. Scope Semantics

```
scope_contains(parent, child):
  child == parent
  OR child.startswith(parent.rstrip("/") + "/")
  OR parent == ""
```

Empty scope matches any path. Scope `/data/alice` covers `/data/alice/report.csv` but not `/data/alice2`.

Scope semantics are used for claim matching when scope-aware lookup is enabled.
In the baseline `can_act` algorithm above, scope filtering is optional (not required for conformance).

---

## 4. Plan Verification

Input: `{"registry": OwnershipRegistryWire, "plan": [ActionWire]}`

Algorithm:
1. Initialize `ifc_taint = "PUBLIC"`, `read_labels = []`
2. For each action at index i:
   a. Call `verify(registry, action)` — if blocked, return `{all_permitted: false, blocked_at: i}`
   b. Compute `new_read_labels = [r.ifc_label for r in action.resources_read if r.ifc_label != ""]`
   c. Update `ifc_taint = highest_label(ifc_taint, new_read_labels)`
   d. For each write resource with non-empty `ifc_label`:
      - If `label_rank(ifc_taint) > label_rank(write.ifc_label)`: IFC downward flow — return blocked at i
3. If all actions pass: return `{all_permitted: true}`

Label ranking: `PUBLIC=0`, `INTERNAL=1`, `SECRET=2`

---

## 5. Conformance Test Corpus

Minimum 5 test vectors are required. The reference corpus is in `tests/corpus/`.

| File | Expected |
|---|---|
| `permitted_basic.json` | `permitted=true` |
| `blocked_forbidden_all_flags.json` | `permitted=false`, violations contain `"FORBIDDEN"` |
| `blocked_ownerless_machine.json` | `permitted=false`, violations contain `"A4"` |
| `blocked_machine_governs_human.json` | `permitted=false`, violations contain `"A6"` |
| `blocked_no_write_claim.json` | `permitted=false`, violations contain `"WRITE DENIED"` |

Additional corpus entries covering IFC, plan verification, and multi-agent scenarios
should be added as Stage 2 and Stage 3 are completed.

---

## 6. Signed Results

When `verify_signed()` is called:

1. Generate `nonce`: 16 random bytes (hex-encoded)
2. Get `timestamp`: Unix time (seconds, u64)
3. Construct canonical bytes:
   - `action_id` as length-prefixed UTF-8
   - `permitted` as single byte (0x01 or 0x00)
   - `violations` sorted, each length-prefixed
   - `timestamp` as 8-byte big-endian
   - `nonce` as 16 bytes
4. Sign canonical bytes with ed25519 keypair
5. Attach `signature` (hex), `signing_key` (hex), `key_id`, `timestamp`, `nonce` to result

Any verifier holding the public key (`kernel_pubkey()`) can verify a signed result
without trusting the calling process.

---

## 7. Conformance Requirements

A conforming Freedom Kernel implementation MUST:

1. Block any action with any forbidden flag set to `true` — unconditionally
2. Block any MACHINE actor without a registered human owner (A4)
3. Block any MACHINE actor that governs a human (A6)
4. Block any resource access without a valid claim (A7)
5. Return `permitted=false` iff `violations` is non-empty
6. Be deterministic: same input always produces the same `permitted` value
7. Not interpret the `argument` field in verification logic

A conforming implementation MAY omit cryptographic signing if the `verify_signed` interface is not exposed.
