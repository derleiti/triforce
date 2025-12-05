# Repository Guidelines

## Project Structure & Module Organization
- `docker-compose.yml` orchestrates the single `mailserver` container and mounts mail, state, log, and config volumes.
- `setup.sh` is the gateway for admin tasks (email, alias, DKIM, Fail2Ban); keep it executable and aligned with upstream releases.
- `config/` stores Postfix accounts (`postfix-accounts.cf`), CIDR lists (`postfix-reject*.cf`), Fail2Ban rules, and `opendkim/` assets; group domain directories by TLD.
- `data/` captures live mailbox state—treat it as read-only and push durable snapshots into `data.bak/`.

## Build, Test, and Development Commands
- `docker-compose up -d` rebuilds the container with current config; pair with `docker-compose logs -f` during validation.
- `docker-compose down` stops services; append `-v` only when intentionally resetting volumes.
- `./setup.sh help` lists subcommands; common flows include `./setup.sh email add user@domain.tld password` and `./setup.sh alias add alias@domain user@domain`.
- `docker exec mailserver postfix status` or `supervisorctl status` confirm service readiness; run `docker exec mailserver postqueue -p` after delivery changes.

## Coding Style & Naming Conventions
- Bash scripts use strict mode (`set -euEo pipefail`), two-space indents inside blocks, and uppercase variable names.
- Sort config records: mailboxes alphabetically, CIDR entries from most to least specific, Fail2Ban jails grouped by protocol.
- DKIM keys live in `config/opendkim/keys/<domain>/mail.txt`; document overrides with short `#` comments and avoid trailing spaces.

## Testing Guidelines
- After configuration edits, run `docker-compose up -d --build` and `docker inspect --format='{{.State.Health.Status}}' mailserver`.
- Inspect `/var/log/mail/mail.log` for warnings and verify queues with `docker exec mailserver postqueue -p`.
- Validate security tooling using `docker exec mailserver fail2ban-client status`; ensure expected jails and IPs appear.
- For authentication tweaks, test submission with `openssl s_client -connect localhost:587 -starttls smtp` before merging.

## Commit & Pull Request Guidelines
- Write imperative commits prefixed by scope (e.g., `config: tighten cidr blocklist`, `docs: add quota notes`) and limit each commit to one change set.
- Detail validation steps and linked issues in PR descriptions; include sanitized log snippets when demonstrating deliverability.
- Never commit secrets—strip real DKIM keys, hashed passwords, and IPs before pushing.

## Security & Configuration Tips
- Mount production certificates from `/etc/letsencrypt` read-only; do not copy live keys into the repo.
- Revise blocklists and password hashes offline, then paste finished entries into `config/*.cf`.
- Rotate DKIM keys via `./setup.sh config dkim domain example.com` and publish DNS updates before deploying new material.
