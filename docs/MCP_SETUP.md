# DOF MCP Server — Setup Guide

The DOF MCP Server exposes governance functions via the **Model Context Protocol** (JSON-RPC 2.0 over stdio). Compatible with Claude Desktop, Cursor, Windsurf, and any MCP client.

## Quick Start

```bash
# List available tools
python3 mcp_server.py --list

# Run as stdio server (for MCP clients)
python3 mcp_server.py
```

## Tools (10)

| Tool | Description |
|------|-------------|
| `dof_verify_governance` | Verify text against constitutional rules (hard + soft) |
| `dof_verify_ast` | Verify Python code against AST security rules |
| `dof_run_z3` | Run Z3 SMT formal verification (4 theorems) |
| `dof_memory_add` | Add governed memory entry |
| `dof_memory_query` | Query memory store with category filter |
| `dof_memory_snapshot` | Bi-temporal memory snapshot |
| `dof_get_metrics` | Compute DOF metrics (SS, GCR, PFI, RP, SSR) |
| `dof_create_attestation` | Create ERC-8004 attestation certificate |
| `dof_oags_identity` | Compute deterministic OAGS agent identity |
| `dof_conformance_check` | Validate OAGS conformance (Levels 1-3) |

## Resources (3)

| URI | Description |
|-----|-------------|
| `dof://constitution` | DOF governance constitution |
| `dof://metrics/latest` | Latest computed metrics |
| `dof://memory/stats` | Memory store statistics |

## Claude Desktop Configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "dof-governance": {
      "command": "python3",
      "args": ["mcp_server.py"],
      "cwd": "/path/to/equipo-de-agentes"
    }
  }
}
```

## Cursor Configuration

Add to `.cursor/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "dof-governance": {
      "command": "python3",
      "args": ["mcp_server.py"],
      "cwd": "/path/to/equipo-de-agentes"
    }
  }
}
```

## Windsurf / Generic MCP Client

```json
{
  "mcpServers": {
    "dof-governance": {
      "command": "python3",
      "args": ["/path/to/equipo-de-agentes/mcp_server.py"],
      "transport": "stdio"
    }
  }
}
```

## Protocol

The server communicates via **JSON-RPC 2.0 over stdio** (one JSON object per line).

### Example: Initialize

```json
→ {"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}
← {"jsonrpc":"2.0","id":1,"result":{"protocolVersion":"2024-11-05","capabilities":{"tools":{},"resources":{}},"serverInfo":{"name":"dof-governance","version":"0.1.0"}}}
```

### Example: Call a tool

```json
→ {"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"dof_verify_governance","arguments":{"output_text":"The analysis shows..."}}}
← {"jsonrpc":"2.0","id":2,"result":{"content":[{"type":"text","text":"{\"status\":\"pass\",\"score\":0.85,...}"}],"isError":false}}
```

### Example: Read a resource

```json
→ {"jsonrpc":"2.0","id":3,"method":"resources/read","params":{"uri":"dof://metrics/latest"}}
← {"jsonrpc":"2.0","id":3,"result":{"contents":[{"uri":"dof://metrics/latest","text":"{\"SS\":0.0,\"GCR\":1.0,...}"}]}}
```

## Dependencies

Zero heavy dependencies. The server uses only Python stdlib + existing DOF core modules:

- `z3-solver` (for Z3 proofs)
- `pyyaml` (for constitution parsing)
- `blake3` (for OAGS identity hashing)

All are already installed as DOF dependencies.

## Testing

```bash
python3 -m unittest tests.test_mcp_server -v
```
