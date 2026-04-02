---
title: Error Handling
impact: MEDIUM
impactDescription: Consistent error codes help debugging
tags: errors, cli, debugging
---

## Error Handling

**Impact: MEDIUM** - Consistent error codes help debugging.

Map failures to known error taxonomy from `references/command-matrix.md`.

**Incorrect:**

```typescript
throw new Error("Something went wrong"); // Too vague
throw new Error("Invalid chain"); // Made up code
```

**Correct:**

```typescript
throw new Error("MISSING_TARGET: --chain flag required"); // Known code
throw new Error("INVALID_ADDRESS: 0x123... is not valid"); // Known code
```

Required:
- Preserve error code semantics: `MISSING_TARGET`, `INVALID_ADDRESS`, `INVALID_CONTRACT`, `INVALID_METHOD`, `CALL_FAILED`
- Provide one concrete next command per failure
- Don't invent new error codes

Reference: [Command Matrix](references/command-matrix.md)
