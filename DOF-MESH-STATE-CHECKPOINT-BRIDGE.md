# 🏛️ DOF-MESH STATE CHECKPOINT: Local Agentic Bridge (Gemma-4)
**Date:** 2026-04-25
**System:** Apple Silicon M4 Max (36GB Unified RAM)
**Component:** `dof_bridge.py` (Anthropic -> Ollama SSE Proxy)

## 🎯 Executive Summary
This session focused on transitioning the local agentic infrastructure from a slow, synchronous proxy to a lightning-fast, asynchronous streaming bridge (`aiohttp`) capable of maintaining the Context Window and bypassing Anthropic's strict CLI validations.

## 🛠️ Architecture & Decisions
1. **Model Residency (VRAM):**
   - Maintained `keep_alive: -1` and `num_ctx: 16384` in the Ollama payload. This ensures the 17GB weights of `Gemma-4-26B-MoE` (`gemma4:26b` in Ollama) remain pinned in unified memory, drastically reducing the TTFT (Time To First Token) for subsequent messages.
2. **Context Window Protection:**
   - Validated that setting the environment variable `CLAUDE_CODE_ATTRIBUTION_HEADER="0"` successfully prevents Claude Code from injecting dynamic `cc_version` and `cch` hashes into the system prompt. This allows Ollama's KV Cache to be reused efficiently.
3. **Streaming Protocol (SSE):**
   - Replaced the single-threaded `http.server` with `aiohttp` to support true Server-Sent Events (SSE). 
   - Strict adherence to the Anthropic event schema (`message_start`, `content_block_start`, `content_block_delta`, `content_block_stop`, `message_delta`, `message_stop`).
4. **Model Name Synchronization:**
   - Modified the proxy to dynamically return the exact model name requested by Claude Code (`Gemma-4-26B-MoE`) instead of Ollama's internal tag (`gemma4:26b`), preventing "malformed response" rejections caused by strict client-side validation.

## 🐛 Critical Bug Fixes (macOS Specific)
- **`OSError: [Errno 22] Invalid argument` in `aiohttp`:**
  - **Issue:** macOS network stacks fail when `aiohttp` attempts to set specific TCP keepalive options on the socket, causing the proxy to crash and instantly drop the connection (leading to `HTTP 200 Malformed Response`).
  - **Fix:** Applied a monkeypatch to `aiohttp.web_protocol.RequestHandler.connection_made` to gracefully catch and ignore the OS-level socket error, allowing the HTTP stream to flow uninterrupted.
- **Strict SSE Formatting:**
  - Standardized all SSE line endings to `\r\n` and ensured mandatory spacing (e.g., `event: message_start`) to prevent the Anthropic CLI parser from choking on perfectly valid JSON payloads.

## 🚀 Current Status & Next Steps
- The bridge is currently running on `http://localhost:4000` via `nohup` with debug logging routed to `/tmp/bridge_debug.log`.
- **Pending Action:** The user needs to authenticate the "cleared" Claude Code CLI session using the dummy key `local-gemma-elite` to resume operations.
- Once authenticated, the agentic workflow is expected to yield sub-second token generation (after the initial model load).
