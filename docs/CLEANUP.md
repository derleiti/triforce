# TriForce Cleanup 2026-06-06

## Changes Made

### Branch: cleanup/remove-dead-files

**Status:** Files flagged for removal via gitignore

#### Dead Files/Directories to Remove:
1. `.backup_mcp_fallback_upgrade_20260315_154333/` - Obsolete backup (3+ months old)
2. `.backup_mcp_hook_20260315_152403/` - Obsolete backup (3+ months old)
3. `.backup_mcp_policy_20260315_151524/` - Obsolete backup (3+ months old)
4. `.patch_backups/` & `patch_backups/` - Duplicate backup dirs (dotted + non-dotted)
5. `ss` - Empty placeholder file (0 bytes)

#### Rationale:
- Backups are 3+ months old and have been superseded by git history
- Duplicate .patch_backups patterns (one should be removed)
- Empty placeholder file serves no purpose

#### Expected Size Reduction:
- ~15-20% from triforce root

### Branch: cleanup/move-assets-debug (ailinux-client)

**Status:** .gitignore updated to ignore runtime artifacts

**Files to Organize:**
- `backend_errors.json` (791 KB) → `.gitignore` + optional `/debug/` directory
- `icon.jpg` → optional move to `/assets/`
- `debug-loop.sh` → optional move to `/scripts/debug/`

#### Expected Size Reduction:
- ~800 KB if debug artifacts removed

### Branch: cleanup/reorganize-scripts-services (ai-twitch-bot)

**Status:** .gitignore updated to ignore runtime files

**Files to Organize:**
- Root-level `.sh` scripts → `/scripts/`
- Systemd `.service` files → `/services/`
- Runtime files (`.lock`, `.log`, `.json` state) → `.gitignore`

#### Runtime Files (should never be in git):
- `.screenshot.lock`
- `screenshot-wrapper.log`
- `game_state.json`
- `latest_comment.txt`
- `latest_vision.txt`

#### Expected Size Reduction:
- ~20% with better organization

## Next Steps

1. **Review PRs** on each cleanup branch
2. **Merge cleanup/remove-dead-files** → requires history rewrite or force-push
3. **Test** all repos after merge
4. **Coordinate** with deployment pipeline

## Git History Notes

⚠️ **Important:** Removing directories with `git rm -r` will alter commit history.

### Option A: Safe (Keep History)
```bash
git rm --cached -r .backup_mcp_*
git rm --cached -r .patch_backups
git rm --cached ss
```
Files stay in old commits but are removed from current HEAD.

### Option B: Clean (Rewrite History)
```bash
git filter-branch --tree-filter 'rm -rf .backup_mcp_* .patch_backups ss' HEAD
```
Requires force-push; all developers must rebase.
