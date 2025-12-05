# Repository Guidelines

## Project Structure & Module Organization
Core WordPress files, themes, and plugins live under `html/`. New plugin work belongs in `html/wp-content/plugins/<slug>/` with supporting assets in `<slug>/assets/`. Persistent data, backup scripts, and DB dumps stay in `mysql/` and `mysql/backups/`. PHP-FPM and Apache configuration overrides reside in `php/` and `apache/httpd.conf`. After creating or syncing files, run `./fix_filepermission.sh` to restore ownership before pushing.

## Build, Test, and Development Commands
Use `docker compose up -d` to start Apache, PHP-FPM, MariaDB, Redis, and workers. Tail logs with `docker compose logs -f apache`, `... wordpress_fpm`, or `... wordpress_db` when validating changes. Confirm the runtime with `docker compose exec wordpress_fpm php -v` (PHP 8.3 expected). Lint plugin entry files via `docker compose exec wordpress_fpm php -l /var/www/html/wp-content/plugins/<slug>/<main>.php`. Bring services down with `docker compose down` (append `-v` to reset the database volume).

## Coding Style & Naming Conventions
Follow WordPress PHP Coding Standards: 4-space indentation, UTF-8, and no closing `?>` in PHP-only files. Prefix functions with the plugin slug in snake_case, e.g., `nova_ai_brainpool_enqueue_assets`. Use StudlyCaps for classes such as `Nova_Ai_Brainpool_Service`. Enqueue scripts and styles from each plugin’s `assets/` directory through WordPress APIs.

## Testing Guidelines
The project relies on manual validation in both the WordPress admin and front end. Watch `docker compose logs -f wordpress_fpm` during smoke tests to catch notices or warnings. Lint every touched PHP file from within the container before committing. Snapshot new UI work with before/after screenshots for PRs.

## Commit & Pull Request Guidelines
Write Conventional Commits in present tense, e.g., `feat(nova-ai-brainpool): add chat UI styles`. Pull requests should include a concise summary, linked issue, reproduction steps, validation notes, and rollback guidance. Attach screenshots for UI changes and document dependencies on services such as `http://host.docker.internal:<port>`. Confirm that linting ran and manual checks passed in the PR body.

## Security & Configuration Tips
Do not commit secrets; store them in `.env` and reference them via `${VAR}` in `docker-compose.yml`. Audit edits to `html/.htaccess` and `apache/httpd.conf` because they affect site-wide routing. Gate optional scripts behind consent helpers like `cmplz_statistics()`, `cmplz_marketing()`, or `cmplz_preferences()` before enqueueing.
