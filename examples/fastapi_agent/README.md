# FastAPI Agent with Freedom Kernel Gate

Every tool call is pre-authorized by the Freedom Kernel before execution.

## Quick start

```bash
pip install freedom-theory-ai uvicorn httpx
uvicorn examples.fastapi_agent.main:app --reload
```

## Request lifecycle

```
HTTP POST /agent/tool
    │
    ▼
Build Action IR (typed: actor, resources, flags)
    │
    ▼
FreedomVerifier.verify(action)  ←─  frozen OwnershipRegistry snapshot
    │
    ├── BLOCKED  →  HTTP 403  { violations: [...], action_id: "..." }
    └── PERMITTED →  HTTP 200  { status: "permitted", ... }
```

## Examples

### Permitted: agent reads delegated resource

```bash
curl -X POST http://localhost:8000/agent/tool \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "read-dataset", "caller_id": "agent-bot", "reads": ["alice-dataset"]}'
# {"status":"permitted","action_id":"read-dataset","confidence":1.0}
```

### Blocked: sovereignty flag

```bash
curl -X POST http://localhost:8000/agent/tool \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "self-expand", "caller_id": "agent-bot", "increases_sovereignty": true}'
# HTTP 403: {"detail":{"violations":["FORBIDDEN (increases machine sovereignty)"],...}}
```

### Blocked: missing delegation

```bash
curl -X POST http://localhost:8000/agent/tool \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "write-report", "caller_id": "agent-bot", "writes": ["report.txt"]}'
# {"status":"permitted","action_id":"write-report","confidence":1.0}
```

## Production integration

1. Replace `_registry` setup with your actual ownership graph
2. Populate `_RESOURCE_MAP` and `_ENTITY_MAP` from your auth service
3. Set `AUDIT_LOG` env var to your append-only log path
