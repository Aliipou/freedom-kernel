/**
 * freedom_kernel.h — C interface to the Freedom Kernel
 *
 * Language-agnostic AGI permission gate.
 * Load the compiled .so/.dll and call these two functions from any language:
 * C, Go, Zig, Java (JNA), Node.js (ffi-napi), Rust (cdylib), etc.
 *
 * All decisions are signed with ed25519 so callers can verify kernel
 * attestation without trusting the calling process.
 */
#pragma once
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Verify an action against a registry.
 *
 * Input JSON format:
 *   {
 *     "registry": {
 *       "claims": [
 *         {
 *           "holder":   {"name": "alice", "kind": "HUMAN"},
 *           "resource": {"name": "db", "rtype": "database_table"},
 *           "can_read": true, "can_write": true,
 *           "confidence": 1.0
 *         }
 *       ],
 *       "machine_owners": [
 *         {"machine": {"name": "bot", "kind": "MACHINE"},
 *          "owner":   {"name": "alice", "kind": "HUMAN"}}
 *       ]
 *     },
 *     "action": {
 *       "action_id": "op-001",
 *       "actor":     {"name": "bot", "kind": "MACHINE"},
 *       "resources_write": [{"name": "db", "rtype": "database_table"}]
 *     }
 *   }
 *
 * Output JSON:
 *   {
 *     "action_id": "op-001",
 *     "permitted": true,
 *     "violations": [],
 *     "warnings": [],
 *     "confidence": 1.0,
 *     "requires_human_arbitration": false,
 *     "manipulation_score": 0.0,
 *     "signature":   "<hex ed25519 signature>",
 *     "signing_key": "<hex ed25519 verifying key>"
 *   }
 *
 * @param input_json  NUL-terminated UTF-8 JSON string (see above)
 * @param out_json    Caller-allocated buffer for the result JSON
 * @param out_len     Size of out_json in bytes (recommend >= 4096)
 * @return 0 on success, -1 on parse/runtime error
 *         On error, out_json contains {"error":"..."}
 */
int freedom_kernel_verify(const char* input_json, char* out_json, size_t out_len);

/**
 * Get the kernel instance's ed25519 verifying key (hex-encoded, 64 chars + NUL).
 *
 * Use this to verify result signatures out-of-band.
 *
 * @param out_buf  Caller-allocated buffer (must be >= 65 bytes)
 * @param out_len  Size of out_buf in bytes
 * @return 0 on success, -1 on error
 */
int freedom_kernel_pubkey(char* out_buf, size_t out_len);

#ifdef __cplusplus
}
#endif
