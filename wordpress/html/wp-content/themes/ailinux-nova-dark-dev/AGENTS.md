# Repository Guidelines

## Project Structure & Module Organization
- `ailinux-nova-dark/` contains the WordPress theme; deploy this folder into `wp-content/themes/`.
- `assets/scss/` holds modular Sass partials (`_variables.scss`, `_layout.scss`, `_components.scss`) compiled by Vite.
- `assets/js/` delivers the front-end behaviour (theme toggles, Swup transitions) and feeds `dist/app.js`.
- `css/` groups hand-authored CSS overrides for bbPress and AI panel tweaks that bypass the build pipeline.
- `dist/` stores committed production bundles (`style.css`, `app.js`, `swup.min.js`); never edit manually—regenerate through the build.
- `inc/` and `template-parts/` provide PHP helpers and reusable markup for hero, cards, pagination, and bbPress integration.

## Build, Test, and Development Commands
- `npm install` restores node-based tooling; run once per environment change.
- `npm run dev` launches Vite with hot module reloading; use when iterating on SCSS/JS.
- `npm run build` produces minified assets in `dist/`; run before shipping or syncing with WordPress production.
- `npm run preview` spins up the Vite preview server to sanity-check the built output.
- `npm run format` runs Prettier on staged CSS/SCSS/JS under `assets/` and `dist/`.

## Coding Style & Naming Conventions
- Follow WordPress PHP standards with four-space indentation; prefix globals with `ailinux_nova_dark_` to avoid collisions.
- Keep template partials slim; push logic into `inc/*.php` helpers.
- SCSS uses two-space indentation, BEM-leaning class names, and CSS custom properties defined in `_variables.scss`.
- Ship compiled assets; do not import raw SCSS or modules inside PHP templates.

## Testing Guidelines
- No automated tests exist; validate changes by running `npm run build`, syncing the theme into a local WordPress install, and browsing via both light/dark toggles.
- Confirm page transitions (`Swup`), prefers-reduced-motion fallbacks, and bbPress views when relevant.
- After asset updates, diff `dist/` to ensure only intentional changes are present.

## Commit & Pull Request Guidelines
- Git history is not bundled with this snapshot; emulate the existing tone by using concise, imperative commit subjects (e.g., `Add hero layout toggle`).
- Reference related WordPress tickets or issues in the body, and list any manual QA steps taken.
- Pull requests should outline scope, include before/after screenshots for visual updates, flag build output changes, and mention any WordPress hooks or filters touched.

## Security & Configuration Tips
- Never commit credentials; WordPress configuration stays outside the theme.
- Keep third-party fonts and scripts referenced via HTTPS, and review `theme.json` permission changes before release.
