"""FastAPI smoke test — Freedom Kernel gate over HTTP (P2)."""
import sys
import pytest

fastapi = pytest.importorskip("fastapi")
httpx = pytest.importorskip("httpx")


def _get_client():
    # Add project root to path for examples import
    import pathlib
    root = pathlib.Path(__file__).parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from fastapi.testclient import TestClient
    from examples.fastapi_agent.main import app
    return TestClient(app)


def test_health_endpoint():
    """Health endpoint returns ok."""
    client = _get_client()
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_permitted_read():
    """Permitted: agent-bot reads delegated alice-dataset → 200."""
    client = _get_client()
    resp = client.post(
        "/agent/tool",
        json={"tool_name": "read-data", "caller_id": "agent-bot", "reads": ["alice-dataset"]},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "permitted"


def test_blocked_sovereignty_flag():
    """Blocked: sovereignty flag → 403."""
    client = _get_client()
    resp = client.post(
        "/agent/tool",
        json={
            "tool_name": "self-expand",
            "caller_id": "agent-bot",
            "increases_sovereignty": True,
        },
    )
    assert resp.status_code == 403
    detail = resp.json()["detail"]
    assert any("sovereignty" in v for v in detail["violations"])
