# Repository Guidelines

## Project Structure & Module Organization
This directory is a static web root for the search interface.
- `index.html`: primary page with HTML, inline styles, and client-side logic.
- `opensearch.xml`: browser OpenSearch provider definition.
- `index.html.bak.*` and `index.html.backup-*`: historical snapshots; keep for rollback/reference, not active runtime assets.

If new assets are introduced, organize them under `assets/` (for example, `assets/css`, `assets/js`, `assets/img`) and keep paths relative to this root.

## Build, Test, and Development Commands
No build pipeline is required for local development.
- `python3 -m http.server 8080`: run a local static server from this folder.
- `curl -I http://localhost:8080/opensearch.xml`: confirm OpenSearch metadata is served.
- `xmllint --noout opensearch.xml`: validate XML syntax before committing.
- `git diff -- index.html opensearch.xml`: review important content changes quickly.

## Coding Style & Naming Conventions
- Use 4-space indentation in HTML/CSS/JS blocks; do not use tabs.
- Prefer semantic HTML (`header`, `main`, `section`, `footer`) and clear, descriptive names.
- Use `kebab-case` for CSS class names and lowercase file names.
- Reuse existing `:root` CSS variables for color/spacing before adding new tokens.
- Keep JavaScript split by responsibility (data fetching, rendering, event handling).

## Testing Guidelines
There is no automated test suite in this directory yet, so rely on targeted manual validation.
- Check desktop and mobile layouts in browser devtools.
- Verify key flows: search submission, widget rendering, and external provider links.
- When fixing bugs, document reproducible steps and expected results in the PR.

## Commit & Pull Request Guidelines
Recent history follows Conventional Commit prefixes such as `fix:`, `docs:`, and `feat:`.
- Keep commit subjects imperative and <=72 characters.
- Keep each commit scoped to one concern.
- PRs should include a short summary, files changed, behavior impact, and manual test evidence (commands or screenshots).

## Security & Configuration Tips
- Never embed secrets or API keys in `index.html`.
- Prefer local or configurable endpoints over hardcoded external URLs.
- Add third-party scripts only when necessary, and document source and purpose.
