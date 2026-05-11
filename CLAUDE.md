الان مهم‌ترین چیز این نیست که «ویژگی اضافه کنی».
مهم‌ترین چیز این است که پروژه را از collapse معماری نجات بدهی.

تو الان در dangerous midpoint هستی:

* نه prototype ساده‌ای
* نه production-grade system

و بیشتر پروژه‌ها دقیقاً همین‌جا می‌میرند.

پس roadmap باید ruthless باشد.

---

# فاز 0 — قانون اساسی پروژه

# (قبل از هر کدی)

اگر این را ننویسی، بعداً پروژه از داخل متلاشی می‌شود.

---

# 0.1 — TCB.md

اولین فایل حیاتی.

باید دقیق تعریف کند:

| Component             | In TCB?    | Why                        |
| --------------------- | ---------- | -------------------------- |
| engine.rs             | YES        | invariant enforcement      |
| crypto.rs             | YES        | attestation integrity      |
| verifier.rs           | YES        | deterministic mediation    |
| planner.rs            | ideally NO | higher-order orchestration |
| NLP                   | NO         | non-formal                 |
| embeddings            | NO         | semantic                   |
| manipulation detector | NO         | heuristic                  |
| LLM runtime           | NO         | nondeterministic           |
| schedulers            | NO         | replaceable policy         |

---

## قانون طلایی:

```text id="r1"
If it requires interpretation,
it is NOT TCB.
```

این باید sacred law شود.

---

# 0.2 — NON_GOALS.md

این document پروژه را نجات می‌دهد.

صریح بنویس:

Freedom Kernel does NOT:

* solve alignment
* infer intent
* understand natural language
* detect truth
* guarantee benevolence
* prevent covert channels
* contain superintelligence
* verify semantic equivalence

این باعث می‌شود expectations انفجاری نشوند.

---

# 0.3 — THREAT_MODEL.md

بدون این، formal verification تقریباً cosmetic است.

باید explicit بنویسی:

## Trusted:

* verifier
* cryptographic primitives
* registry integrity

## Untrusted:

* LLMs
* humans
* prompts
* schedulers
* tools
* IPC payloads
* embeddings

## Out of scope:

* side-channel attacks
* timing leakage
* steganography
* compromised kernels
* malicious owners

---

# فاز 1 — capability algebra

# مهم‌ترین بخش کل پروژه

قبل از scheduler.
قبل از runtime.
قبل از AGI fantasies.

---

# 1.1 — capability.rs

نه implementation سنگین.

فقط algebra.

مثلاً:

```rust id="r2"
enum CapabilityKind {
    Read,
    Write,
    Delegate,
    Spawn,
    IPCSend,
    IPCReceive,
    ConsumeQuota,
    EnterDomain,
}
```

---

# 1.2 — attenuation semantics

باید formally تعریف کنی:

```text id="r3"
child_capability ⊆ parent_capability
```

بدون ambiguity.

---

# 1.3 — transfer semantics

فرق این‌ها باید crystal clear باشد:

| Operation | Meaning               |
| --------- | --------------------- |
| delegate  | temporary subset      |
| transfer  | ownership move        |
| attenuate | weaker capability     |
| clone     | duplicate authority   |
| lease     | time-bound delegation |
| revoke    | invalidate capability |

اگر این early formalize نشود،
بعداً جهنم consistency می‌شود.

---

# 1.4 — revocation model

این خیلی مهم است.

Revocation سخت‌تر از delegation است.

باید تصمیم بگیری:

## eager revocation

یا

## lazy revocation

و tradeoffها را explicit کنی.

---

# فاز 2 — typed IR hardening

الان Action model هنوز زیادی abstract است.

باید close-world شود.

---

# 2.1 — ممنوعیت Stringly-Typed Hell

این خطرناک است:

```rust id="r4"
HashMap<String, Value>
```

یا:

```rust id="r5"
permissions: Vec<String>
```

این formalism را می‌کشد.

---

# 2.2 — Action taxonomy

همه actionها finite باشند:

```rust id="r6"
enum ActionKind {
    ReadResource,
    WriteResource,
    SendIPC,
    SpawnAgent,
    ConsumeQuota,
    EnterDomain,
}
```

---

# 2.3 — Explicit side effects

هیچ side effect implicit نباشد.

مثلاً:

❌ بد:

```text id="r7"
Action("search_web")
```

✅ خوب:

```text id="r8"
Read(network:web)
Write(cache:search_results)
ConsumeQuota(api_tokens)
```

---

# فاز 3 — formal boundary defense

الان بزرگ‌ترین خطر:
semantic creep است.

---

# 3.1 — ممنوعیت NLP داخل kernel

هرگز:

* regex policy
* semantic similarity
* embedding checks
* intent inference
* LLM classification

داخل TCB نرود.

هرگز.

---

# 3.2 — deterministic purity CI check

CI باید fail کند اگر:

* randomness
* time dependency
* network access
* filesystem mutation

داخل engine.rs بیاید.

---

# 3.3 — LOC budget

جدی می‌گویم:

برای engine.rs سقف LOC بگذار.

مثلاً:

```text id="r9"
Hard limit: 500 LOC
```

چون TCB inflation واقعی‌ترین خطر است.

---

# فاز 4 — real systems engineering

اینجا پروژه از research toy جدا می‌شود.

---

# 4.1 — benchmark suite

لازم داری:

* verification latency
* plan verification scaling
* spawn chain costs
* IPC throughput
* memory usage

---

# 4.2 — fuzzing

باید brutal fuzzing داشته باشی.

مخصوصاً:

* malformed claims
* recursive delegation
* cyclic graphs
* capability overflow
* TOCTOU races

---

# 4.3 — adversarial suite

این مهم‌تر از unit tests است.

مثلاً:

* privilege escalation attempts
* covert delegation
* fake revocation
* taint laundering
* recursive spawn attacks

---

# فاز 5 — minimal runtime

نه OS کامل.
نه AGI platform.

فقط:
reference runtime.

---

# 5.1 — ipc.rs

فقط mediated channels.

نه distributed magic.

---

# 5.2 — quota.rs

ساده:

* token budgets
* spawn budgets
* API budgets

---

# 5.3 — scheduler.rs

تا جای ممکن dumb.

Scheduler policy نباید TCB شود.

---

# فاز 6 — ecosystem credibility

الان پروژه technically interesting است.
ولی هنوز socially untrusted است.

---

# 6.1 — rename positioning

روی این branding برو:

```text id="r10"
Capability-security kernel
for autonomous systems
```

نه:

* AGI kernel
* ethics engine
* superalignment runtime

---

# 6.2 — serious demos

مثلاً:

* OpenAI tool execution
* LangGraph orchestration
* AutoGen spawning
* MCP mediation

---

# 6.3 — external review

باید security people واقعی repo را critique کنند.

اگر فقط AI people ببینند،
feedback کافی نمی‌گیری.

---

# مهم‌ترین توصیه کل roadmap

## complexity را به edges هل بده.

و:

## core را stupidly small نگه دار.

---

# قانون طلایی نهایی

اگر feature جدید:

* semantic interpretation می‌خواهد
* probabilistic reasoning می‌خواهد
* NLP می‌خواهد
* ML inference می‌خواهد
* dynamic policy می‌خواهد

احتمال زیاد:

## داخل kernel تعلق ندارد.

---

# چیزی که پروژه می‌تواند بشود

اگر discipline حفظ شود:

* seccomp برای agentic systems
* OPA برای AI execution
* capability microkernel برای autonomous runtimes

---

# چیزی که پروژه را نابود می‌کند

* ego expansion
* universal ethics claims
* semantic creep
* TCB inflation
* abstraction addiction

این‌ها قاتل‌های واقعی‌اند.
