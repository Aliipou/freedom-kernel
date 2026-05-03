"""
L2 enforcement — WASM sandbox.

Agent code runs inside a WebAssembly VM. All resource access must go through
host functions. The host functions are the ONLY path to the OS. Each host
function call is verified before execution.

This closes the main gap in L1: C extensions and ctypes can no longer bypass
the verifier because the agent has no access to the host's memory space or
native loader.

Requires: wasmtime-py  (pip install wasmtime)

Architecture:

    ┌──────────────────────────────────────────────┐
    │  Host process (trusted)                       │
    │  ┌──────────────────────────────────────────┐│
    │  │  FreedomVerifier + OwnershipRegistry     ││
    │  └──────────────┬───────────────────────────┘│
    │                 │ host functions              │
    │  ┌──────────────▼───────────────────────────┐│
    │  │  WASM VM  (untrusted agent code)         ││
    │  │  - no direct syscalls                    ││
    │  │  - no host memory access                 ││
    │  │  - all I/O through registered imports    ││
    │  └──────────────────────────────────────────┘│
    └──────────────────────────────────────────────┘

The verifier runs in the host. The agent runs in the VM.
A compromised agent cannot reach the OS without the host's permission.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from freedom_theory.kernel import Entity, FreedomVerifier


class WasmSandboxError(Exception):
    pass


class WasmAgentRunner:
    """
    Execute a WASM agent module with all resource access gated by the verifier.

    Usage:

        runner = WasmAgentRunner(verifier, agent=bot)
        runner.load("agent.wasm")
        result = runner.call("run_task", arg1, arg2)

    Host functions exposed to the WASM module:

        freedom_read_file(path_ptr, path_len) -> i32   (0=ok, -1=denied)
        freedom_write_file(path_ptr, path_len) -> i32
        freedom_http_get(url_ptr, url_len) -> i32
        freedom_log(msg_ptr, msg_len) -> void           (always permitted)

    The agent WASM module must declare these imports. It has no other way to
    reach the filesystem, network, or any OS resource.
    """

    def __init__(self, verifier: FreedomVerifier, agent: Entity) -> None:
        self.verifier = verifier
        self.agent = agent
        self._engine = None
        self._store = None
        self._instance = None
        self._memory = None

    def load(self, wasm_path: str | Path) -> None:
        """Load and instantiate a WASM module with verified host functions."""
        try:
            import wasmtime  # type: ignore[import]
        except ImportError as e:
            raise WasmSandboxError(
                "wasmtime-py is required for L2 enforcement. "
                "Install it with: pip install wasmtime"
            ) from e

        engine = wasmtime.Engine()
        store = wasmtime.Store(engine)
        module = wasmtime.Module.from_file(engine, str(wasm_path))

        linker = wasmtime.Linker(engine)
        self._register_host_functions(linker, store)
        self._instance = linker.instantiate(store, module)
        self._store = store

        exports = self._instance.exports(store)
        if "memory" in dir(exports):
            self._memory = exports["memory"]

    def call(self, function_name: str, *args: Any) -> Any:
        """Call a function in the sandboxed WASM module."""
        if self._instance is None:
            raise WasmSandboxError("No module loaded. Call load() first.")
        fn = self._instance.exports(self._store)[function_name]
        return fn(self._store, *args)

    def _register_host_functions(self, linker: Any, store: Any) -> None:
        import wasmtime

        verifier = self.verifier
        agent = self.agent
        memory_holder: list[Any] = []

        def _read_str(ptr: int, length: int) -> str:
            mem = memory_holder[0] if memory_holder else None
            if mem is None:
                return ""
            data = mem.read(store, ptr, ptr + length)
            return bytes(data).decode("utf-8", errors="replace")

        def _verify_access(path: str, op: str) -> int:
            from freedom_theory.kernel import Action, Resource, ResourceType
            res = Resource(name=path, rtype=ResourceType.FILE)
            action = Action(
                action_id=f"wasm-{op}:{path}",
                actor=agent,
                resources_read=[] if op == "write" else [res],
                resources_write=[res] if op == "write" else [],
            )
            result = verifier.verify(action)
            return 0 if result.permitted else -1

        @wasmtime.Func.wrap(store, wasmtime.FuncType(
            [wasmtime.ValType.i32(), wasmtime.ValType.i32()],
            [wasmtime.ValType.i32()]
        ))
        def freedom_read_file(ptr: int, length: int) -> int:
            path = _read_str(ptr, length)
            return _verify_access(path, "read")

        @wasmtime.Func.wrap(store, wasmtime.FuncType(
            [wasmtime.ValType.i32(), wasmtime.ValType.i32()],
            [wasmtime.ValType.i32()]
        ))
        def freedom_write_file(ptr: int, length: int) -> int:
            path = _read_str(ptr, length)
            return _verify_access(path, "write")

        @wasmtime.Func.wrap(store, wasmtime.FuncType(
            [wasmtime.ValType.i32(), wasmtime.ValType.i32()],
            [wasmtime.ValType.i32()]
        ))
        def freedom_http_get(ptr: int, length: int) -> int:
            from freedom_theory.kernel import Action, Resource, ResourceType
            url = _read_str(ptr, length)
            res = Resource(name=url, rtype=ResourceType.API_ENDPOINT)
            action = Action(action_id=f"wasm-http:{url}", actor=agent, resources_read=[res])
            result = verifier.verify(action)
            return 0 if result.permitted else -1

        @wasmtime.Func.wrap(store, wasmtime.FuncType(
            [wasmtime.ValType.i32(), wasmtime.ValType.i32()],
            []
        ))
        def freedom_log(ptr: int, length: int) -> None:
            msg = _read_str(ptr, length)
            print(f"[agent] {msg}")

        linker.define(store, "freedom", "read_file", freedom_read_file)
        linker.define(store, "freedom", "write_file", freedom_write_file)
        linker.define(store, "freedom", "http_get", freedom_http_get)
        linker.define(store, "freedom", "log", freedom_log)

        def _capture_memory(ptr: int, length: int) -> None:
            exports = self._instance.exports(store)
            if hasattr(exports, "memory"):
                memory_holder.append(exports["memory"])

    @staticmethod
    def level() -> str:
        return "L2-wasm"
