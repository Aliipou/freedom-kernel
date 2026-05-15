"""
AuditLog — structured, append-only audit trail for FreedomVerifier decisions.

Every call to FreedomVerifier.verify() that has an AuditLog attached appends
one JSON record. Records include timestamp, action_id, permitted, confidence,
violations, warnings, and optional cryptographic signature.
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AuditLog:
    """
    Append-only structured audit log for verification decisions.

    Usage:
        log = AuditLog(path="/var/log/kernel.jsonl")
        verifier = FreedomVerifier(registry, audit_log=log)
        # every verify() call is logged automatically

    path=None keeps entries in-memory only.
    """
    path: str | None = None
    _records: list[dict[str, Any]] = field(
        default_factory=list, init=False, repr=False
    )
    _lock: threading.Lock = field(
        default_factory=threading.Lock, init=False, repr=False
    )

    def record(self, result: Any) -> None:
        """Append a verification result to the log (called by FreedomVerifier)."""
        entry: dict[str, Any] = {
            "ts": time.time(),
            "action_id": result.action_id,
            "permitted": result.permitted,
            "confidence": result.confidence,
            "violations": list(result.violations),
            "warnings": list(result.warnings),
            "signature": getattr(result, "signature", None),
        }
        with self._lock:
            self._records.append(entry)
            if self.path is not None:
                with open(self.path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry) + "\n")

    def entries(self) -> list[dict[str, Any]]:
        """Return a snapshot of all in-memory log entries."""
        with self._lock:
            return list(self._records)

    def __len__(self) -> int:
        with self._lock:
            return len(self._records)
