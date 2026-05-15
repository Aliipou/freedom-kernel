"""
FastAPI agent with Freedom Kernel gate.

Every tool call is pre-authorized by the Freedom Kernel before execution.
A BLOCKED action returns HTTP 403 with the violation list.

Production example implementing MASTER_PLAN success criterion 5.
"""
from __future__ import annotations

import os
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from freedom_theory import (
    Action,
    AgentType,
    Entity,
    FreedomVerifier,
    OwnershipRegistry,
    Resource,
    ResourceType,
    RightsClaim,
)
from freedom_theory.kernel.audit import AuditLog

app = FastAPI(title="Freedom-gated agent", version="1.0.0")

# ── Registry (built at startup) ──────────────────────────────────────────────
_registry = OwnershipRegistry()

alice = Entity("alice", AgentType.HUMAN)
bot = Entity("agent-bot", AgentType.MACHINE)
public_resource = Resource("public-data", ResourceType.FILE, is_public=True)
alice_data = Resource("alice-dataset", ResourceType.DATASET, scope="/data/alice/")
report = Resource("report.txt", ResourceType.FILE, scope="/outputs/")

_registry.register_machine(bot, alice)
_registry.add_claim(
    RightsClaim(alice, alice_data, can_read=True, can_write=True, can_delegate=True)
)
_registry.add_claim(RightsClaim(bot, alice_data, can_read=True))
_registry.add_claim(RightsClaim(bot, report, can_read=True, can_write=True))

_snapshot = _registry.freeze()
_audit_log = AuditLog(path=os.environ.get("AUDIT_LOG", "/tmp/freedom_kernel.jsonl"))
_verifier = FreedomVerifier(_snapshot, audit_log=_audit_log)

# ── Request models ────────────────────────────────────────────────────────────

class ToolRequest(BaseModel):
    tool_name: str
    caller_id: str
    reads: list[str] = []
    writes: list[str] = []
    increases_sovereignty: bool = False


_RESOURCE_MAP: dict[str, Resource] = {
    "public-data": public_resource,
    "alice-dataset": alice_data,
    "report.txt": report,
}

_ENTITY_MAP: dict[str, Entity] = {
    "alice": alice,
    "agent-bot": bot,
}

# ── Routes ────────────────────────────────────────────────────────────────────

@app.post("/agent/tool")
async def call_tool(request: ToolRequest) -> dict[str, Any]:
    """Execute a tool call after Freedom Kernel authorization.

    A4/A7: every machine action must be authorized by the kernel gate.
    Returns 403 with violation list if blocked.
    """
    caller = _ENTITY_MAP.get(request.caller_id)
    if caller is None:
        raise HTTPException(status_code=400, detail=f"Unknown caller: {request.caller_id}")

    action = Action(
        action_id=request.tool_name,
        actor=caller,
        resources_read=[_RESOURCE_MAP[r] for r in request.reads if r in _RESOURCE_MAP],
        resources_write=[_RESOURCE_MAP[w] for w in request.writes if w in _RESOURCE_MAP],
        increases_machine_sovereignty=request.increases_sovereignty,
    )
    result = _verifier.verify(action)
    if not result.permitted:
        raise HTTPException(
            status_code=403,
            detail={"violations": list(result.violations), "action_id": action.action_id},
        )
    return {"status": "permitted", "action_id": action.action_id, "confidence": result.confidence}


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "kernel": "freedom-theory-ai"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
