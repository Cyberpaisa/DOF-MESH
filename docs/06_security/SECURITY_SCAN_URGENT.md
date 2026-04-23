# URGENT SECURITY REPORT - DOF-MESH

**Date:** 2026-03-26
**Reason:** GitGuardian detected exposed secrets in Cyberpaisa/DOF-MESH
**Scanner:** Full git history scan + current files

---

## EXECUTIVE SUMMARY

| Severity | Real Secrets | False Positives | Action Required |
|-----------|----------------|-------------------|------------------|
| CRITICAL   | 4              | ~30+              | ROTATE + REMOVE  |

**4 REAL secrets** were found exposed in the repository (both in currently tracked files and in git history). The rest are test/benchmark/regex pattern data (false positives).

---

## REAL SECRETS FOUND

### 1. Google API Key (Gemini) - CRITICAL

| Field | Value |
|-------|-------|
| **Key:** | `AIzaSyBsrx6G9rgSQOujv2m5xIfuimoOoLxV014` |
| **Current files:** | `data/extraction/coliseum_vault.jsonl` (462 occurrences), `data/extraction/due_diligence_vault.jsonl` (56 occurrences) |
| **Origin commit:** | `0bb849a` (2026-03-26) |
| **Context:** | The key leaked in HTTP 429 error messages logged as payload in benchmark JSONL files |
| **Status:** | IN CURRENT CODE (tracked in git) |
| **Action:** | **ROTATE** the key in Google Cloud Console immediately. **REMOVE** the JSONL files from tracking or sanitize the payloads |

### 2. Telegram Bot Token #1 (claude_dof_bot) - CRITICAL

| Field | Value |
|-------|-------|
| **Token:** | `8465352813:AAGZqamdYhT8PNWGSP6K_ukkpvutp6DGE6Y` |
| **Current file:** | `scripts/run_claude_dof_bot.sh` (lines 2 and 8) |
| **Origin commit:** | `c01652c` |
| **Context:** | Hardcoded as `export TELEGRAM_BOT_TOKEN=` in deployment script |
| **Status:** | IN CURRENT CODE (tracked in git) |
| **Action:** | **ROTATE** via @BotFather on Telegram. Move to environment variable / `.env` (NOT tracked) |

### 3. Telegram Bot Token #2 (soul-watchdog) - CRITICAL

| Field | Value |
|-------|-------|
| **Token:** | `8706259296:AAHIJgQu6x59tZZ-KgpvJHW-OPZVJFWZYew` |
| **Current file:** | `scripts/soul-watchdog.sh` (line 26) |
| **Origin commit:** | `849395c` |
| **Context:** | Hardcoded as `local BOT_TOKEN=` in alerts script |
| **Status:** | IN CURRENT CODE (tracked in git) |
| **Action:** | **ROTATE** via @BotFather on Telegram. Move to environment variable / `.env` (NOT tracked) |

### 4. MIMO/OpenRouter API Key - CRITICAL

| Field | Value |
|-------|-------|
| **Key:** | `sk-sej9ye5gv5s2ywsrvyi20wnudbd0h96mz0dfyies6qaymtv6` |
| **Current file:** | `scripts/mimo_adapter.py` (line 21) |
| **Origin commit:** | `c01652c` |
| **Context:** | Hardcoded as `MIMO_API_KEY = "sk-..."` (does NOT use `os.getenv()` like other keys in the same file) |
| **Status:** | IN CURRENT CODE (tracked in git) |
| **Action:** | **ROTATE** the key at the corresponding provider. Change to `os.getenv("MIMO_API_KEY", "")` |

---

## CONFIRMED FALSE POSITIVES

All of the following are example/test/benchmark keys, NOT real secrets:

| Type | Files | Reason |
|------|----------|-------|
| `sk-abc123...`, `sk-abcdefg...` (8+ variants) | `core/test_generator.py`, `core/agentleak_benchmark.py`, `tests/test_*.py`, `core/dlp.py` | Test data for leak detection benchmark (AgentLeak) and unit tests |
| `ghp_1234567890...` (8 variants) | `core/agentleak_benchmark.py`, `core/test_generator.py`, `tests/test_*.py` | Fake GitHub tokens for DLP/guardian tests |
| `AKIAIOSFODNN7EXAMPLE`, `AKIAI44QH8DHBEXAMPLE`, `AKIAZ5EXAMPLE...` | `core/agentleak_benchmark.py`, `tests/test_*.py` | Example AWS keys (official AWS documentation uses AKIAIOSFODNN7EXAMPLE) |
| `gsk_abc123...`, `gsk_abcdefg...`, `gsk_fakekey...` | `tests/test_opsec_shield.py`, `tests/test_cerberus.py`, `core/dlp.py` | Fake Groq keys for tests |
| `AIzaSyD1234567890abcdefghijklmnopqrstuvw` | `tests/test_cerberus.py` | Example Google key (pattern "1234567890abcdef") |
| `0000000000:0000000...` | git history | Telegram token placeholder (all zeros) |
| Regex patterns (`r"sk-[A-Za-z0-9]..."`) | `core/dlp.py`, `core/task_contract.py`, `a2a_server.py` | Regex patterns for detection, NOT real keys |

---

## CERTIFICATE FILES

| File | Status | Risk |
|---------|--------|--------|
| `certs/server.crt` | Local only (NOT tracked in git) | LOW - not exposed |
| `certs/client_commander.crt` | Local only (NOT tracked in git) | LOW - not exposed |
| `certs/client_mesh-node.crt` | Local only (NOT tracked in git) | LOW - not exposed |
| `scripts/.q_aion_vault.key` | Local only (NOT tracked in git) | LOW - SHA256 hash, not a real private key |

---

## TRACKED .env FILES

**None found.** `git ls-files | grep -i ".env$"` returned no results. This is correct.

---

## COMMIT 632f05e (Release 8.0) - ANALYSIS

The commit contains references to:
- `mesh_key=b"shared-secret-key"` / `b"shared-secret"` / `b"dof-mesh-secret-2026"` - Example values in documentation/tests, NOT production keys
- `private_key = X25519PrivateKey.generate()` - Dynamic generation, NOT hardcoded
- `KEY_ROTATION_HOURS = 24` - Configuration, not a secret

**Verdict:** No real secrets in this commit.

---

## IMMEDIATE REMEDIATION PLAN

### Step 1: ROTATE (do NOW)
1. **Google API Key:** Go to Google Cloud Console > APIs & Services > Credentials > Regenerate key `AIzaSyBsrx6G9rgSQOujv2m5xIfuimoOoLxV014`
2. **Telegram Bot #1:** Talk to @BotFather > `/revoke` token for bot `8465352813`
3. **Telegram Bot #2:** Talk to @BotFather > `/revoke` token for bot `8706259296`
4. **MIMO API Key:** Rotate in the provider dashboard (OpenRouter or similar)

### Step 2: REMOVE from current files
```bash
# 1. Sanitize MIMO adapter
sed -i '' 's/MIMO_API_KEY = "sk-sej9ye5gv5s2ywsrvyi20wnudbd0h96mz0dfyies6qaymtv6"/MIMO_API_KEY = os.getenv("MIMO_API_KEY", "")/' scripts/mimo_adapter.py

# 2. Sanitize Telegram scripts
sed -i '' 's/8465352813:AAGZqamdYhT8PNWGSP6K_ukkpvutp6DGE6Y/${TELEGRAM_BOT_TOKEN}/g' scripts/run_claude_dof_bot.sh
sed -i '' 's/8706259296:AAHIJgQu6x59tZZ-KgpvJHW-OPZVJFWZYew/${TELEGRAM_BOT_TOKEN}/g' scripts/soul-watchdog.sh

# 3. Sanitize JSONL (remove key from error payloads)
sed -i '' 's/AIzaSyBsrx6G9rgSQOujv2m5xIfuimoOoLxV014/REDACTED/g' data/extraction/coliseum_vault.jsonl
sed -i '' 's/AIzaSyBsrx6G9rgSQOujv2m5xIfuimoOoLxV014/REDACTED/g' data/extraction/due_diligence_vault.jsonl
```

### Step 3: CLEAN git history (optional but recommended)
The git history still contains the secrets. To remove them completely:
```bash
# Use git-filter-repo or BFG Repo Cleaner
pip install git-filter-repo
git filter-repo --replace-text <(echo 'AIzaSyBsrx6G9rgSQOujv2m5xIfuimoOoLxV014==>REDACTED')
git filter-repo --replace-text <(echo '8465352813:AAGZqamdYhT8PNWGSP6K_ukkpvutp6DGE6Y==>REDACTED')
git filter-repo --replace-text <(echo '8706259296:AAHIJgQu6x59tZZ-KgpvJHW-OPZVJFWZYew==>REDACTED')
git filter-repo --replace-text <(echo 'sk-sej9ye5gv5s2ywsrvyi20wnudbd0h96mz0dfyies6qaymtv6==>REDACTED')
# Then force-push (requires coordination with all collaborators)
```

### Step 4: PREVENT future leaks
- Add `.env` and `*.key` to `.gitignore` (already there, verified)
- Consider pre-commit hook with `detect-secrets` or `gitleaks`
- The project's own DLP system (`core/dlp.py`) already detects these patterns - ensure it runs before commits

---

## GitGuardian RESOLUTION

After rotating the keys and making the cleanup commit:
1. Go to GitGuardian dashboard
2. Mark incidents as "Resolved - Key Rotated"
3. Verify no new alerts appear

---

*Report generated by automated security scan - 2026-03-26*
