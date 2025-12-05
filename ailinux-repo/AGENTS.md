# Repository Guidelines

## Project Structure & Module Organization
This repo orchestrates the AILinux apt mirror and its nginx front-end. `docker-compose.yml` and the root `Dockerfile` define the two-container stack. Operational entry points (`update-mirror.sh`, `postmirror.sh`, `maintain.sh`, `generate-index.sh`, `monitor-indexes.sh`, `heal-perms.sh`) live at the top level for cron or manual runs. `repo/` is the mounted apt-mirror spool (mirror/, var/, etc/)—treat it as cache and stage only small control files such as `mirror.list`. Configuration sits in `conf.d/` (nginx includes) and `etc/` (`nginx/` HTML, `gnupg/` keyring, `ssl/` mounts). Diagnostics land in `log/` and `logs/`; `scripts/sign-repos.sh` feeds `postmirror.sh`.

## Build, Test, and Development Commands
- `docker compose build apt-mirror`: rebuild the mirror image after Dockerfile or package changes.
- `docker compose up -d`: start apt-mirror and nginx; inspect with `docker compose logs --tail 80 apt-mirror`.
- `./update-mirror.sh --dry-run`: checks access, locks, and arch detection without writes; drop `--dry-run` for a full sync.
- `./generate-index.sh`: refresh the public directory listing and `repo/mirror/index.html`.
- `./maintain.sh`: launch the maintenance menu that chains updates, signing, and the Nova live log.

## Coding Style & Naming Conventions
Automation is Bash; start files with `#!/usr/bin/env bash`, enable `set -euo pipefail`, and indent two spaces. Prefer hyphenated filenames and `UPPER_SNAKE_CASE` for exported environment variables. Guard optional tooling with `command -v` and run `shellcheck <script>` before sending changes.

## Testing Guidelines
Validate every change with `./health.sh` (DNS, TLS, endpoint checks) and `./repo-health.sh /root/ailinux-repo/repo/mirror` to confirm signed `InRelease` files. For nginx routing updates run `docker compose exec nginx nginx -t` and hit `curl -fsS https://repo.ailinux.me:8443/mirror/Release` (adjust host or port for local tests). Monitor syncs with `tail -f log/update-mirror.log` or `./monitor-indexes.sh 10` while troubleshooting long fetches.

## Commit & Pull Request Guidelines
Use short, imperative subjects with optional type prefixes (`fix: restore dep11 cleanup`, `maintain: refresh index`). Add context, risk, and validation notes in the body. Pull requests should note affected suites, list executed scripts/logs, and show before/after snippets for nginx or mirror.list edits. Never commit generated artifacts from `repo/mirror/**`, transient logs, or private material from `etc/gnupg`.

## Security & Operations Tips
Keep signing secrets in `etc/gnupg` (`chmod 700`) and never stage them; use `export-public-key.sh` to publish the public key. Lock long jobs with `log/apt-mirror.update.lock` instead of ad-hoc mutexes. After ownership changes, run `./heal-perms.sh` to keep nginx and the containers reading keys, logs, and mirror outputs.
