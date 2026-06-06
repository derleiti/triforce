# TriForce Cleanup Plan — 2026-06-06

## Overview

Comprehensive cleanup of directory structure and removal of dead/obsolete files across the AILinux ecosystem.

---

## 1. TriForce Backend (`derleiti/triforce`)

### Branch: `cleanup/remove-dead-files`

**Dead Files/Directories:**
| File/Dir | Size | Age | Action |
|----------|------|-----|--------|
| `.backup_mcp_fallback_upgrade_20260315_154333/` | ? | 3+ mo | DELETE |
| `.backup_mcp_hook_20260315_152403/` | ? | 3+ mo | DELETE |
| `.backup_mcp_policy_20260315_151524/` | ? | 3+ mo | DELETE |
| `.patch_backups/` | ? | unknown | DELETE |
| `patch_backups/` | ? | unknown | MERGE INTO `.patch_backups/` |
| `ss` | 0 B | unknown | DELETE |
| `discover.tf` | 226 B | ? | MOVE → `infrastructure/terraform/` |
| `versions.tf` | 172 B | ? | MOVE → `infrastructure/terraform/` |

**Redundant Scripts (Root):**
- `install.sh`, `install-rammode.sh`, `triforce-rammode.sh`
- `patch_login_logout_redirect.sh`, `patch_wp_logout_bridge.sh`
- `init-update.sh`, `start-init-update.sh`, `update.sh`

**Action:** Consolidate into `/scripts/`:
```
scripts/
├── install/
│   ├── install.sh
│   ├── install-rammode.sh
│   └── triforce-rammode.sh
├── patch/
│   ├── patch-login-logout.sh
│   └── patch-wp-logout.sh
└── update/
    ├── update.sh
    ├── init-update.sh
    └── start-init-update.sh
```

**Documentation Consolidation:**
- Move all root `.md` files → `/docs/README.md` or organized index
- Consolidate: `AGENTS.md`, `GEMINI.md`, `DEPLOY_LOG.md`, `SERVER_DOCUMENTATION.md`, `cli-agents.md`, `TSP_PROTOCOL.md`

**Expected Reduction:** 15-20%

---

## 2. AILinux Client (`derleiti/ailinux-client`)

### Branch: `cleanup/move-assets-debug`

**Dead Weight:**
| File | Size | Issue |
|------|------|-------|
| `backend_errors.json` | 791 KB | Debug dump, should be ignored |
| `icon.jpg` | 139 KB | Should be in `/assets/` |
| `debug-loop.sh` | ? | Should be in `/scripts/debug/` |

**Proposed Structure:**
```
ailinux_client/
├── assets/
│   └── icon.jpg
├── scripts/
│   └── debug-loop.sh
├── debug/
│   └── [optional: backend error logs]
├── ailinux_client/
└── run.py
```

**Action:**
1. Create `/assets/` directory
2. Move `icon.jpg` to `/assets/`
3. Create `/scripts/debug/` directory
4. Move `debug-loop.sh` to `/scripts/debug/`
5. Update `.gitignore` to ignore `backend_errors.json`

**Expected Reduction:** ~800 KB

---

## 3. AI-Twitch-Bot (`derleiti/ai-twitch-bot`)

### Branch: `cleanup/reorganize-scripts-services`

**Runtime Files (Should Not Be in Git):**
| File | Size | Action |
|------|------|--------|
| `.screenshot.lock` | 0 B | DELETE / IGNORE |
| `screenshot-wrapper.log` | 0 B | DELETE / IGNORE |
| `game_state.json` | ? | DELETE / IGNORE |
| `latest_comment.txt` | 360 B | DELETE / IGNORE |
| `latest_vision.txt` | 1.6 KB | DELETE / IGNORE |
| `__pycache__/` | ? | Verify in `.gitignore` |

**Scripts to Reorganize (Move to `/scripts/`):**
```
scripts/
├── screenshot/
│   ├── screenshot.sh
│   ├── screenshot-wrapper.sh
│   └── start-qwen-server.sh
├── bot/
│   ├── start-zephyr.sh
│   └── restart-zephyr.sh
├── debug/
│   ├── collect_logs.sh
│   └── _safe_run_analyze
```

**Services to Reorganize (Move to `/services/`):**
```
services/
├── zephyrbot.service
├── zephyr-screenshot.service
└── qwen-vl-server.service
```

**Action:**
1. Add runtime files to `.gitignore`
2. Create `/scripts/` subdirectories
3. Create `/services/` directory
4. Move files while preserving references

**Expected Reduction:** 15-20%

---

## 4. AI-Coder (`derleiti/ai-coder`)

### Branch: `cleanup/entrypoint-refactor`

**Tiny Wrapper Fix:**
- `aicoder_main.py` (132 bytes) — only imports `aicoder/__init__.py`
- **Action:** Move content to `aicoder/__main__.py`, delete wrapper

**Expected Impact:** <1%

---

## 5. Copa (`derleiti/copa`)

### Branch: `cleanup/entrypoint-refactor`

**Tiny Wrapper Fix:**
- `app.py` (82 bytes) — only imports `copa/`
- **Action:** Move content to `copa/__main__.py`, delete wrapper

**Expected Impact:** <1%

---

## Execution Strategy

### Phase 1: Safety (Current)
✅ Create cleanup branches with `.gitignore` updates
✅ Document all changes in commit messages

### Phase 2: Review (Next)
- [ ] Review PRs on each branch
- [ ] Validate no critical files are being removed
- [ ] Verify `.gitignore` patterns work correctly

### Phase 3: Merge (After Review)
- [ ] Merge `cleanup/remove-dead-files` to master
- [ ] Test full build pipeline
- [ ] Merge other cleanup branches in sequence

### Phase 4: Communication
- [ ] Notify team about directory structure changes
- [ ] Update deployment/CI scripts with new paths
- [ ] Update documentation with new structure

---

## Total Expected Impact

| Repo | Current | After | Reduction |
|------|---------|-------|-----------|
| **triforce** | 452 MB | ~380 MB | 15-20% |
| **ailinux-client** | ? | -800 KB | ~? |
| **ai-twitch-bot** | ? | -15-20% | TBD |
| **ai-coder** | ? | <1% smaller | Negligible |
| **copa** | ? | <1% smaller | Negligible |

**Total Ecosystem Reduction:** ~10-15% overall

---

## Git History Considerations

⚠️ **Removing files rewrites history.** Two options:

### Option A: Safe (Recommended)
```bash
git rm --cached -r .backup_mcp_*
git commit -m "cleanup: remove from index (history preserved)"
```
- Files stay in old commits
- Clean current directory
- No force-push required

### Option B: Clean History
```bash
git filter-branch --tree-filter 'rm -rf .backup_mcp_*' HEAD
git push origin master --force
```
- Files completely removed from history
- All developers must rebase
- Use only if necessary

**Recommendation:** Use **Option A** for safety and ease of rollback.

---

## Checklist

- [ ] Create all cleanup branches
- [ ] Update `.gitignore` files
- [ ] Document changes in commit messages
- [ ] Create PRs for review
- [ ] Get approvals
- [ ] Merge to main branches
- [ ] Run full test suite
- [ ] Update CI/CD pipelines with new paths
- [ ] Notify team of structure changes
- [ ] Monitor for any broken references

