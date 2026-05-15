# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.2.x   | ✓         |
| 0.1.x   | ✗         |

## Reporting a Vulnerability

**Do NOT open a public GitHub Issue for security vulnerabilities.**

Use GitHub Private Security Advisories:
https://github.com/Aliipou/freedom-kernel/security/advisories/new

### Response SLA

| Severity | Acknowledgement | Initial Response | Fix Target |
|----------|----------------|-----------------|------------|
| Critical | 24h            | 48h             | 7d         |
| High     | 48h            | 7d              | 30d        |
| Medium   | 7d             | 14d             | 90d        |

## In Scope

- Any bypass that changes a verification result from BLOCKED to PERMITTED
- Panic in any verification path (denial-of-service)
- Cryptographic weakness in ed25519 signing or canonical serialization
- Audit log tampering that is undetectable
- C ABI buffer overflow or out-of-bounds read/write
- Lock poisoning that produces incorrect verification results

## Out of Scope

- Issues in example code under `examples/`
- DoS via inputs exceeding `FREEDOM_KERNEL_MAX_INPUT` (these are rejected by design)
- Theoretical attacks requiring physical access to the signing key

## Disclosure Process

1. Advisory draft created in GitHub Security Advisories
2. Fix prepared in a private branch
3. CVE requested from GitHub or MITRE
4. Coordinated release: fix + public advisory published together
5. `CHANGELOG.md` entry prefixed with `[Security]`
