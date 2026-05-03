# Enforcement Architecture

**Branch**: `kernel-grade`

---

## The core gap

The current project is a **capability policy library**, not a **capability kernel**.

The difference:

| | Policy library | Capability kernel |
|---|---|---|
| Caller cooperation | Required | Not required |
| Enforcement | Advisory | Mandatory |
| Bypass | Trivial — ignore the result | Requires compromising the kernel |
| Analogy | Security guidelines | seccomp, SELinux, seL4 |

In the current architecture, a malicious or misconfigured agent can simply not call `verify()`, or ignore a BLOCKED result, or import a C extension and call `open()` directly. The verifier is never in the mandatory path.

This is not a criticism unique to this project. It is the fundamental limitation of any library-level capability system. Capsicum, CHERI, and seL4 solve it at the OS or hardware level. We are working at the application level.

This document defines what real enforcement requires and the path to get there.

---

## Enforcement layers

### Layer 0: Advisory (current state on `main`)

```
Agent code → calls verify() voluntarily → executes or halts
```

The verifier is called by the agent framework adapter. Nothing prevents the agent from bypassing the adapter. Correct behavior depends entirely on caller cooperation.

**When this is sufficient**: trusted development environments, policy auditing, frameworks where the adapter is the only path to tool execution.

**When this is insufficient**: any adversarial setting where the agent code itself is untrusted.

---

### Layer 1: Soft enforcement — Python audit hooks (current state on `kernel-grade`)

```
Agent code → open()/subprocess/socket → Python audit hook → verifier → permit/PermissionError
```

Python 3.8+ `sys.addaudithook()` fires before every file open, subprocess launch, and network connection at the Python level. The hook raises `PermissionError` to block. Once installed, the hook **cannot be removed** — Python deliberately prevents hook removal to stop auditors from being bypassed.

```python
from freedom_theory.enforcement import CapabilityEnforcer

enforcer = CapabilityEnforcer(verifier, agent=bot)
enforcer.install()  # permanent — cannot be undone

# From this point: any open() not covered by a valid claim raises PermissionError
open("/data/alice/secret.txt")  # → PermissionError if bot has no read claim
```

**What this enforces**: `open()`, `os.open()`, `subprocess.Popen()`, `os.system()`, `socket.connect()`.

**What this does NOT enforce**: C extensions calling the OS directly, `ctypes` calling `libc`, any code that bypasses Python's interpreter. If the agent can load a C extension, it can bypass the audit hook.

**Strength**: stronger than advisory; weaker than OS isolation.

---

### Layer 2: WASM sandbox (planned)

```
Agent code (WASM) → host function → verifier → permit/trap
```

Agent logic runs inside a WASM virtual machine. All resource access must go through WASM host functions. The host functions are the only way to reach the OS. Each host function call goes through the verifier first.

The WASM VM enforces a hard boundary: WASM code cannot call OS APIs directly. The verifier is in the mandatory path by construction.

**What this enforces**: every resource access by the agent, regardless of language.

**What this does NOT enforce**: the host itself — if the host process is compromised, the isolation is gone. The WASM sandbox enforces the capability discipline for the agent; the host is still in the TCB.

**Status**: WASM bindings exist (`freedom-kernel/src/wasm.rs`). WASM agent runner is not yet built. This is the next planned enforcement layer.

Design sketch:

```
┌─────────────────────────────────────────┐
│  Host process (trusted)                  │
│  ┌────────────────────────────────────┐ │
│  │  FreedomVerifier + OwnershipGraph  │ │
│  └──────────────┬─────────────────────┘ │
│                 │ host functions         │
│  ┌──────────────▼─────────────────────┐ │
│  │  WASM VM (untrusted agent code)    │ │
│  │  - no direct syscalls              │ │
│  │  - all I/O through host functions  │ │
│  │  - memory isolated from host       │ │
│  └────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

---

### Layer 3: OS-level isolation (planned)

```
Agent process → syscall → seccomp/BPF filter → kernel → permitted ops only
```

The agent runs in a separate process. A seccomp BPF filter limits the syscalls available to the agent. The filter is installed before agent code runs and cannot be removed by the agent.

The verifier runs in a separate trusted process. The agent communicates with it via a restricted IPC channel (Unix socket or pipe). The agent cannot read or write files without going through the IPC channel, which routes through the verifier.

This is the same architecture as a microkernel or a capability OS:
- The kernel (verifier process) is the only entity with full privileges
- Agents are unprivileged processes that request capabilities via IPC
- The OS enforces isolation between processes

**What this enforces**: everything the OS enforces — files, sockets, subprocesses, memory, shared memory.

**What this does NOT enforce**: colluding processes with pre-shared capabilities, the trusted verifier process itself.

**Status**: planned. Requires Linux or macOS seccomp/sandbox integration. Not yet implemented.

---

## Current enforcement status

| Threat | Layer 0 (advisory) | Layer 1 (audit hook) | Layer 2 (WASM) | Layer 3 (OS) |
|---|---|---|---|---|
| Agent ignores BLOCKED result | NOT enforced | Enforced | Enforced | Enforced |
| Agent opens file directly | NOT enforced | Enforced (Python) | Enforced | Enforced |
| Agent spawns subprocess | NOT enforced | Enforced (Python) | Enforced | Enforced |
| Agent calls C extension | NOT enforced | NOT enforced | Enforced | Enforced |
| Agent uses ctypes | NOT enforced | NOT enforced | Enforced | Enforced |
| Compromised host process | NOT enforced | NOT enforced | NOT enforced | NOT enforced |
| Memory corruption in verifier | NOT enforced | NOT enforced | NOT enforced | NOT enforced |

---

## What seL4 does that this project does not (yet)

seL4 enforces capability discipline at the microkernel level:
- Every IPC, memory mapping, and device access requires a capability
- Capabilities are unforgeable tokens managed by the kernel
- The kernel is formally verified — the C implementation is proved to match the abstract specification
- The scheduler, IPC, and memory management are all in the TCB

This project's TCB is ~330 lines of verification logic. seL4's TCB is ~10,000 lines of C with a machine-checked proof. The gap is years of work, not a design flaw.

The honest answer to "is this kernel-grade?" is:
- The **specification** is kernel-grade — the axioms, invariants, and formal proofs are in the right lineage
- The **enforcement** is library-grade today — Layer 1 is soft; Layers 2 and 3 are planned
- Reaching seL4-level trust requires Layers 2 or 3 plus external hostile review

---

## Path forward

1. **Now** (Layer 1): Python audit hook is in `enforcement/hooks.py`. Mandatory for Python-level operations.

2. **Next** (Layer 2): Build the WASM agent runner. Agents run in a WASM VM; all resource access through host functions that call the verifier. This is the most practical path to strong enforcement without OS integration.

3. **After that** (Layer 3): Linux seccomp + Unix socket IPC between agent process and verifier process. This is real OS-level capability enforcement.

4. **Long term**: Formal proof that the WASM host function interface is sound — i.e., that every path from WASM code to a resource goes through the verifier. This is the equivalent of seL4's proof that every IPC goes through the kernel.
