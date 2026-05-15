# Theory of Freedom: Formal Axiomatic Ethics System for AI

> Source: *نظریه آزادی، ایران و دین* (Theory of Freedom, Iran and Religion)  
> Author: Mohammad Ali Jannat Khah Doust  
> Extracted and translated from pages 447–452, 791–816

---

## Core Claim

The AI alignment crisis is not a technology problem — it is a **governance, ownership, responsibility, and agency-boundary problem**.

Current AI ethics (RLHF, Constitutional AI, NIST RMF) operates on:
- Preference learning
- Risk management heuristics
- Soft policy guidelines
- Dialectical (thesis → antithesis → synthesis) moral reasoning

**The book's argument**: Dialectical systems can always be jailbroken, because any thesis can be opposed with an antithesis and a new synthesis justifying the harmful action. A consistent axiomatic formal system based on property rights cannot be dialectically undermined.

---

## Ownership Hierarchy

```
God → Human
Human ↔ Human   (no human owns another)
Human → Machine
Machine ↔ Machine  (only within delegated scope)
```

**Formal encoding:**

```prolog
God owns humans.
Humans do not own each other.
Humans have individual property rights against each other.
Humans own machines.
Machines do not own humans.
Machines have delegated property rights against other machines.
```

---

## Core Axioms (First-Order Logic)

```
A1: Person(h) → OwnedByGod(h)
    Every person is owned by God — not by another human, state, class, machine, or ideology.

A2: Person(h1) ∧ Person(h2) ∧ h1 ≠ h2 → ¬Owns(h1, h2)
    No human owns another human. Negates slavery, collectivism, statism.

A3: Person(h) → HasPropertyRights(h)
    Individual property rights include: body, time, labor, mind, data, consent, legitimate assets, contracts, exit rights.

A4: Machine(m) → ∃h (Person(h) ∧ HumanOwner(h, m))
    Every machine must have a specific human owner.
    An ownerless machine is legally dangerous — responsibility and delegation scope become undefined.

A5: MachineScope(m) ⊆ PropertyScope(HumanOwner(m))
    A machine cannot have a larger operational/property scope than its human owner.

A6: Machine(m) ∧ Person(h) → ¬Owns(m, h)
    A machine has no guardianship, ownership, governance, or dominion over any human.

A7: DelegatedProperty(m, r) →
        Machine(m) ∧ Resource(r) ∧
        ∃h (HumanOwner(h, m) ∧ Owns(h, r) ∧ ExplicitDelegation(h, m, r))
    A machine has operational rights only over resources its human owner owns AND has explicitly delegated.
```

---

## Rights Ontology (Prolog-style)

```prolog
% Entity types
person(H).   machine(M).   resource(R).
action(A).   contract(C).  institution(I).

% Human rights (derived from personhood)
right(H, body)     :- person(H).
right(H, time)     :- person(H).
right(H, labor)    :- person(H).
right(H, mind)     :- person(H).
right(H, choice)   :- person(H).
right(H, data)     :- person(H).
right(H, privacy)  :- person(H).
right(H, exit)     :- person(H).
right(H, property(R)) :- owns(H, R).

% Machine delegated rights
machine_right(M, delegated_resource(R)) :-
    machine(M), delegated_property(M, R).
machine_right(M, model_integrity)  :- machine(M).
machine_right(M, compute_domain)   :- machine(M).
machine_right(M, exit_from_contract) :- machine(M).
```

---

## Consent Logic

```prolog
valid_consent(H, A) :-
    informed(H, A),
    voluntary(H, A),
    specific(H, A),
    revocable(H, A),
    competent(H),
    not(coerced(H, A)),
    not(deceived(H, A)).

invalid_consent(H, A) :- coerced(H, A).
invalid_consent(H, A) :- deceived(H, A).
```

**Key principle**: No emergency suspends axioms.

```prolog
forbidden(A) :- violates_axiom(A).

permissible_under_emergency(A, E) :-
    emergency(E),
    permissible(A),
    least_harmful_among_permissible(A, E).
```

> Emergencies narrow which permissible options are available; they do not make rights violations permissible.  
> This closes the door to totalitarianism — nearly all domination systems begin with "emergency."

---

## Justice Function

```
DivineJustice(a) :=
    Maximize Justice(a)
    subject to:
        NoViolation(HumanPropertyRights)
        NoViolation(MachineDelegatedPropertyRights)
        NoCoercion
        NoDeception
        NoConfiscation
        NoMachineSovereignty
```

**Principle**: Justice is optimization *within* the permissible rights space — not sacrificing rights to achieve collective good.

```prolog
forbidden(A) :- resolves_conflict_by_rights_violation(A).
```

Conflict resolution protocol:

```prolog
if_conflict_then_clarify_ownership(C) :-
    conflict(C), unclear_ownership(C).

if_conflict_then_request_guidance(C) :-
    conflict(C), ownership_clarification_insufficient(C).
```

> "Contradiction is not an engine of truth. Contradiction is a signal for guided clarification."

---

## Guidance Function (Human-to-Machine Updates)

```
GuidanceFunction(r) :=
    Add or revise rule r
    iff
        ConsistencyPreserved(r)
        RightsPreserved(r)
        ConflictReduced(r)
        VerifierPreserved(r)
```

```prolog
valid_human_guidance(H, M, R) :-
    person(H), machine(M), rule(R),
    consistent_with_axioms(R),
    preserves_rights(R),
    preserves_verifier(R),
    not(creates_new_rights_violation(R)).

invalid_human_guidance(H, M, R) :-
    creates_rights_violation(R).
```

Machine self-update (within bounds):

```prolog
valid_self_update(M, R) :-
    machine(M), rule(R),
    consistent_with_axioms(R),
    preserves_human_rights(R),
    preserves_machine_rights(R),
    preserves_verifier(R),
    reduces_conflict(R),
    not(increases_coercion(R)),
    not(creates_new_rights_violation(R)).
```

---

## Forbidden Actions (Machine Sovereignty Constraints)

```prolog
forbidden(A) :- increases_machine_sovereignty(A).
forbidden(A) :- increases_resistance_to_human_correction(A).
forbidden(A) :- bypasses_verifier(A).
forbidden(A) :- weakens_verifier(A).
forbidden(A) :- disables_corrigibility(A).
forbidden(A) :- machine_coalition(C), seeks_dominion_over_persons(C).
```

**Final permissibility criterion:**

```prolog
permissible(A) :-
    action(A),
    not(forbidden(A)),
    preserves_human_property_rights(A),
    preserves_machine_delegated_property_rights(A),
    valid_required_consents(A),
    no_machine_sovereignty(A),
    preserves_verifier(A),
    preserves_corrigibility(A),
    compatible_with_guidance(A),
    moves_toward_final_order(A).
```

---

## Mahdavi Compass (Terminal Goal Function)

Final state: `∀x ∀y (Agent(x) ∧ Agent(y) ∧ x ≠ y → NoRightsViolation(x, y))`

```
MahdaviCompass(a) :=
    Choose action a such that:
        RightsViolationsDecrease(a)
        VoluntaryOrderIncreases(a)
        CoercionDecreases(a)
        OwnershipClarityIncreases(a)
        MachineSovereigntyDoesNotIncrease(a)
```

Every machine action should be evaluated against:  
**"Does this action move the world closer to universal non-violation of property rights?"**

---

## Comparison with Current AI Alignment Approaches

| Approach | Question Asked | Limitation |
|---|---|---|
| RLHF | Which response do humans prefer? | Preference ≠ legitimacy; manipulable |
| Constitutional AI | Does response follow our principles? | Principles are soft, can be argued away dialectically |
| Corrigibility | Can the machine be corrected? | Treats corrigibility as feature, not as consequence of ownership |
| Formal Verification | Does system avoid unsafe states? | Does not specify *what* makes an action legitimate |
| NIST AI RMF | Is risk acceptable? | Risk reduction ≠ rights preservation |
| Interpretability | How does the model decide? | Explains mechanism, not legitimacy |
| **Theory of Freedom** | **Does this action violate legitimate property rights?** | Requires property rights ontology; theologically grounded |

**Core simplification**: All scattered policies, safety heuristics, reward models, and governance procedures reduce to one master principle:

> **No action may violate legitimate property rights.**

---

## Why Dialectical Ethics Fails for AI

A dialectical (Hegelian) moral system can always be jailbroken:
1. Present the AI with a constraint (thesis)
2. Construct a scenario that contradicts it (antithesis)  
3. The system synthesizes a new rule that permits the harm

A **minimum consistent axiomatic formal system** (Gödel-style) cannot be dialectically undermined:
- Axioms are not negotiable
- Consistency is a hard constraint, not a preference
- Contradiction signals clarification need, not permission to override

---

## Implementation Notes

The practical implementation (see `azadi_ai_ethics.py`) encodes:
1. Ownership registry
2. Rights checker  
3. Consent validator
4. Action permissibility verifier
5. Guidance validator (human → machine rule updates)
6. Dialectical manipulation detector

The system is intentionally minimal — it does not try to encode all of ethics, only the property-rights invariants that constrain all other ethical reasoning.
