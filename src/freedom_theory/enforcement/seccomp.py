"""
L3 enforcement — seccomp BPF syscall filter.

Install a syscall whitelist on the current process before running agent code.
The kernel enforces this at the syscall boundary — no Python-level bypass is
possible. Even C extensions and native libraries are restricted.

This is the same mechanism used by Chrome's renderer sandbox, Docker's default
profile, and OpenSSH's privilege separation.

Requires: Linux kernel 3.17+, libseccomp  (pip install seccomp   or   apt install python3-seccomp)

Usage:

    from freedom_theory.enforcement.seccomp import install_agent_profile

    install_agent_profile()   # call before running any agent code
    # From this point: only whitelisted syscalls are permitted.
    # socket(), execve(), ptrace(), mount() → EPERM

The profile is irreversible for the current process. Fork a child process
before calling this if you need to restore full privileges in the parent.
"""
from __future__ import annotations

import platform

# Syscalls required for a Python interpreter to function.
# This is the minimal set: I/O, memory, threading primitives, signals.
_PYTHON_RUNTIME_ALLOW = [
    # I/O
    "read", "write", "pread64", "pwrite64", "readv", "writev",
    "sendfile", "splice",
    # File descriptors
    "open", "openat", "close", "dup", "dup2", "dup3",
    "stat", "fstat", "lstat", "newfstatat",
    "lseek", "llseek",
    "fcntl", "ioctl",
    "pipe", "pipe2",
    # Memory
    "brk", "mmap", "mmap2", "munmap", "mremap", "mprotect",
    "madvise", "mincore",
    # Process/thread
    "exit", "exit_group",
    "clone",           # for threading (not exec); restrict flags in production
    "set_robust_list", "get_robust_list",
    "futex",
    # Signal handling
    "rt_sigaction", "rt_sigprocmask", "rt_sigreturn",
    "sigaltstack",
    # Time
    "clock_gettime", "clock_nanosleep", "nanosleep",
    "gettimeofday", "time",
    # Identity (read-only)
    "getpid", "getppid", "gettid", "getuid", "getgid",
    "geteuid", "getegid", "getgroups",
    # Misc Python runtime needs
    "getrandom", "uname", "sysinfo",
    "getcwd", "chdir",
    "readlink", "readlinkat",
    "getdents", "getdents64",
    "umask",
    "set_tid_address",
    "arch_prctl", "prctl",      # Python uses these
    "epoll_create1", "epoll_wait", "epoll_ctl",
    "select", "pselect6", "poll", "ppoll",
    "eventfd", "eventfd2",
    "timerfd_create", "timerfd_settime", "timerfd_gettime",
    # Directory ops (needed for imports)
    "mkdir", "mkdirat", "rmdir",
    "unlink", "unlinkat",
    "rename", "renameat", "renameat2",
    "symlink", "symlinkat",
    "link", "linkat",
    "truncate", "ftruncate",
    "chmod", "fchmod", "fchmodat",
    "chown", "fchown", "fchownat", "lchown",
    # Memory-mapped files
    "msync", "flock",
    # Scheduling
    "sched_getaffinity", "sched_setaffinity",
    "sched_yield",
]

# Syscalls that are NEVER permitted for agent code.
# These are the syscalls that enable privilege escalation, network access,
# process injection, and filesystem namespace manipulation.
_DENY_SYSCALLS = [
    "socket", "connect", "bind", "listen", "accept", "accept4",
    "sendto", "recvfrom", "sendmsg", "recvmsg",
    "socketpair",
    "execve", "execveat",
    "fork", "vfork",
    "ptrace",
    "mount", "umount2", "pivot_root", "chroot",
    "unshare", "setns",
    "sethostname", "setdomainname",
    "iopl", "ioperm",
    "kexec_load", "kexec_file_load",
    "perf_event_open",
    "userfaultfd",
    "bpf",
    "seccomp",          # prevent agent from weakening the filter
    "keyctl", "add_key", "request_key",
]


def install_agent_profile() -> None:
    """
    Install the agent seccomp profile on the current process.

    IRREVERSIBLE — once installed, the filter cannot be removed.
    Fork a child process before calling this if the parent needs full access.

    Raises:
        RuntimeError  — not on Linux, or libseccomp not available
        OSError       — kernel rejected the filter (check kernel version >= 3.17)
    """
    if platform.system() != "Linux":
        raise RuntimeError(
            f"seccomp is only available on Linux (current: {platform.system()}). "
            "For non-Linux systems, use L1 (audit hook) or L2 (WASM sandbox) enforcement."
        )

    try:
        import seccomp  # type: ignore[import]
    except ImportError as e:
        raise RuntimeError(
            "libseccomp Python bindings are required for L3 enforcement. "
            "Install with: pip install seccomp  (requires libseccomp-dev)"
        ) from e

    # Default: kill the process on any syscall not in the whitelist.
    # Use ERRNO(EPERM) instead of KILL for softer enforcement (agent gets EPERM).
    f = seccomp.SyscallFilter(defaction=seccomp.ERRNO(1))  # 1 = EPERM

    for name in _PYTHON_RUNTIME_ALLOW:
        try:
            f.add_rule(seccomp.ALLOW, name)
        except RuntimeError:
            # Syscall may not exist on this architecture — skip silently
            pass

    f.load()


def generate_docker_seccomp_profile() -> str:
    """
    Generate a JSON seccomp profile for Docker/OCI container runtimes.
    Apply with: docker run --security-opt seccomp=agent_profile.json ...

    Returns the JSON string.
    """
    import json

    profile = {
        "defaultAction": "SCMP_ACT_ERRNO",
        "architectures": ["SCMP_ARCH_X86_64", "SCMP_ARCH_X86", "SCMP_ARCH_X32"],
        "syscalls": [
            {
                "names": _PYTHON_RUNTIME_ALLOW,
                "action": "SCMP_ACT_ALLOW",
            }
        ],
    }
    return json.dumps(profile, indent=2)
