---
name: api-design-principles
description: REST API design principles for DOF SDK endpoints (FastAPI). Use when designing new API routes, reviewing API specs, or extending the MCP/A2A server.
---

# API Design Principles — DOF Adapted

REST API design principles for the DOF SDK, tailored to FastAPI and the existing API layer.

## When to Use This Skill

- Designing new REST endpoints for `dof/api.py` or `a2a_server.py`
- Extending the MCP server interface
- Creating new governance or observability API routes
- Reviewing API specifications before implementation

## DOF-Specific Conventions

- All API responses include governance metadata (`governance_pass`, `score`, `violations`)
- Use Pydantic models (already used in FastAPI layer)
- All outputs go to JSONL for audit trail
- No LLM for governance decisions — always deterministic
- Error responses follow DOF's `GovernanceResult` pattern

## Resource Design for DOF

```python
# DOF API endpoints follow resource-oriented design
GET    /api/v1/traces              # List run traces (paginated)
GET    /api/v1/traces/{run_id}     # Get specific trace
POST   /api/v1/governance/check    # Run governance check on text
POST   /api/v1/ast/verify          # Run AST verification on code
GET    /api/v1/metrics             # Get current metrics (SS, PFI, RP, GCR, SSR)
GET    /api/v1/constitution        # Get active constitution rules
POST   /api/v1/memory/add          # Add governed memory entry
POST   /api/v1/memory/query        # Query governed memory
GET    /api/v1/storage/status      # Get storage backend status
```

## Pagination Pattern (DOF Standard)

```python
from pydantic import BaseModel, Field
from typing import List, Optional

class PaginationParams(BaseModel):
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)

class PaginatedResponse(BaseModel):
    items: List[dict]
    total: int
    page: int
    page_size: int
    pages: int
```

## Error Response Pattern

```python
from pydantic import BaseModel
from typing import Optional

class DOFErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[dict] = None
    governance_context: Optional[dict] = None

# Status codes
# 200 — governance check passed
# 400 — invalid input (bad text, unparseable code)
# 422 — governance violation (hard rule blocked)
# 500 — internal error
```

## Governance-Aware Responses

Every DOF API response that processes LLM output includes:

```python
class GovernanceResponse(BaseModel):
    status: str          # "pass" | "fail"
    score: float         # 0.0–1.0
    violations: list     # hard rule violations
    warnings: list       # soft rule warnings
    output: Optional[str] = None
```

## Best Practices for DOF

1. **Resource nouns**: `/traces`, `/metrics`, `/constitution` — not `/runGovernance`
2. **Stateless**: each request carries all context (no server sessions)
3. **Deterministic**: same input → same governance result (no randomness)
4. **Audit trail**: every API call that modifies state writes to JSONL
5. **Pagination**: always paginate trace/memory collections
6. **Versioning**: use URL prefix `/api/v1/` for future compatibility
7. **Documentation**: FastAPI auto-generates OpenAPI/Swagger docs

## Common Pitfalls

- Using POST for idempotent read operations (use GET)
- Returning raw exceptions instead of structured `DOFErrorResponse`
- Missing JSONL audit log for state-changing endpoints
- Not including governance metadata in responses
- Tight coupling between API routes and internal `core/` module APIs
