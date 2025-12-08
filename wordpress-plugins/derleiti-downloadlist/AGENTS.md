# Repository Guidelines

## Project Structure & Module Organization
`derleiti-downloadlist.php` bootstraps the download shortcode, AJAX handlers, and admin menu. Nova AI features live in `nova-ai-frontend/`: `includes/` houses PHP classes for hooks and settings, while `assets/` serves JS, CSS, the manifest, icons, and the service worker. Keep enqueue handles and paths aligned whenever assets are renamed or moved.

## Build, Test, and Development Commands
Control the plugin locally with WP-CLI: `wp plugin activate derleiti-downloadlist` and `wp plugin deactivate derleiti-downloadlist`. Lint PHP before committing—`php -l derleiti-downloadlist.php nova-ai-frontend/nova-ai-frontend.php`. Validate crawler adjustments by forcing the hook: `wp cron event run --due-now nova_ai_crawler_tick`. After front-end edits, hard-refresh or clear the service worker cache because files are delivered without a bundler.

## Coding Style & Naming Conventions
Follow the WordPress PHP standard: four-space indentation, brace-on-next-line classes, and sanitize external input with helpers like `esc_url_raw`, `wp_normalize_path`, and `absint`. Under the `NovaAI` namespace, expose PascalCase classes and UPPER_SNAKE_CASE constants. JavaScript sticks to ES5-compatible syntax with two-space indentation and camelCase variables; guard optional browser APIs before calling them. Reuse the `nova-` and `derleiti-` prefixes when coining new CSS selectors.

## Testing Guidelines
No automated suite exists yet, so combine linting with targeted manual checks. Render `[derleiti_downloads]`, request a file, and confirm the secure AJAX download and admin notes display correctly. For Nova AI, test FAB visibility, chat submissions, and offline notifications for both subscriber and admin roles. Capture console or network traces for API issues and summarize findings in the pull request.

## Commit & Pull Request Guidelines
Version control happens in downstream Git mirrors; keep commit subjects imperative and under roughly 72 characters (e.g., `Add crawler schedule guard`). Merge related work into reviewable commits rather than stacking fixups. In your PR, describe the change, list validation commands or scenarios, attach UI screenshots or recordings when UX shifts, and link any tracking issues. Call out backward-compatibility or deployment impacts up front.

## Security & Configuration Tips
Store API endpoints and download paths via WordPress options—never hard-code secrets. When touching filesystem logic, normalize paths and verify permissions to prevent traversal or read failures. Before release, disable debug logging and bump the service worker so cached clients pick up updated API hosts.
