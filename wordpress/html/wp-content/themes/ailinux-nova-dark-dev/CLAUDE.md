# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Theme Overview

**Ailinux Nova Dark** is a modern WordPress theme with dark-first design inspired by ChatGPT's aesthetic. Features include generous whitespace, smooth Swup page transitions, integrated AI discussion panel, WebGPU support for enhanced visualizations, and bbPress forum integration.

**Working Directory**: `/home/zombie/wordpress/html/wp-content/themes/ailinux-nova-dark-dev/`

This is the **active development theme** and the only version currently in use. The `ailinux-nova-dark/` directory (without `-dev` suffix) is obsolete and should not be edited.

**IMPORTANT**: All theme development must be done in `ailinux-nova-dark-dev/` only. This is a standalone theme directory with its own build pipeline.

## Development Commands

### Build & Development
```bash
npm install                 # Install dependencies (first time only)
npm run dev                # Start Vite dev server with HMR
npm run build              # Build production assets to dist/
npm run preview            # Preview production build locally
npm run format             # Format JS/SCSS/CSS with Prettier
```

**CRITICAL**: Always run `npm run build` after modifying files in `assets/js/` or `assets/scss/`. WordPress loads assets from `dist/`, not source files.

### Theme Packaging
```bash
zip -r ailinux-nova-dark.zip ailinux-nova-dark-dev -x "*/node_modules/*" "*/.git/*"
```

## Architecture

### Build System (Vite)
**Config**: `vite.config.js` - Uses ESBuild minification, no code splitting, static filenames for WordPress compatibility

**Source → Output**:
- `assets/js/` → `dist/*.js`
- `assets/scss/` → `dist/style.css`

**Entry points** (defined in vite.config.js rollupOptions.input):
- `app.js` - Main application logic (AilinuxNovaApp module, Swup transitions)
- `color-mode.js` - Color mode initialization (blocks render to prevent FOUC)
- `customizer.js` - WordPress Customizer live preview
- `mobile-menu.js` - Mobile navigation panel with overlay
- `webgpu.js` - WebGPU support with Canvas 2D fallback
- `style.scss` - Main stylesheet (imports all SCSS partials)

**Important**: Vite output uses static filenames (`[name].js`, `[name][extname]`) without hashes, enabling WordPress to enqueue files by predictable paths.

### Key WordPress Integration

**functions.php** - Central theme setup:
- Constants: `AILINUX_NOVA_DARK_VERSION`, `AILINUX_NOVA_DARK_DIR`, `AILINUX_NOVA_DARK_URI`
- Asset versioning via `ailinux_nova_dark_get_asset_version()` (uses file mtime)
- Theme setup, widget areas, customizer, schema markup
- bbPress integration and optimizations
- Navigation menu handling with forum detection

**Template Hierarchy**:
- Standard WordPress templates in root: `index.php`, `single.php`, `archive.php`, `page.php`, `search.php`, `404.php`
- `home.php` - Custom homepage with hero section
- `comments.php` - Comment template
- `header.php`, `footer.php` - Layout wrappers
- `sidebar.php` - Sidebar widget area
- `searchform.php` - Search form

**Template Parts** (`template-parts/`):
- `content-hero.php` - Featured post display (sticky or latest)
- `content-card.php` - Blog post cards for grid/list layouts
- `content-single.php` - Single post content with TOC
- `content-none.php` - No results found
- `related-posts.php` - Related posts section
- `pagination.php` - Enhanced pagination with jump links

### JavaScript Architecture

**app.js** (`AilinuxNovaApp` module):
- Header scroll behavior (sticky, hide on scroll down)
- Navigation overflow handling (responsive "More ▼" menu)
- Reading time calculation (200 WPM constant)
- IntersectionObserver for fade-in animations (respects `prefers-reduced-motion`)
- Table of Contents generation for H2/H3 headings (sticky positioning)
- Smooth scroll for anchor links
- AI Discussion panel integration with retry logic

**AilinuxNovaTransitions** (Swup integration):
- Page transitions via `#swup` container
- Re-initializes app on `page:view` hook
- Auto-disables on bbPress forum links (`data-no-swup`)

**mobile-menu.js**:
- Toggle via `#mobile-menu-toggle` (hamburger → X animation)
- Slide-in panel from right (`#mobile-nav-panel`)
- Submenu expansion for `.menu-item-has-children`
- Body scroll locking when open

**webgpu.js** (`AilinuxWebGPU` class):
- WebGPU initialization with adapter/device setup
- Automatic fallback to Canvas 2D if WebGPU unavailable
- Used for enhanced AI visualizations

**color-mode.js**:
- Runs immediately in `<head>` (blocking) to prevent FOUC
- Reads `localStorage.getItem('color-mode')` or `prefers-color-scheme`
- Sets `data-color-mode="dark|light"` on `<html>`
- Toggle implementation in main app.js

### AI Discussion Feature
- Floating panel triggered by `#ai-discuss-btn`
- Configured via `NOVA_API` localized script object:
  - `BASE` - API base URL (customizer setting, default: `https://api.ailinux.me:9000`)
  - `CHAT_ENDPOINT` - Chat endpoint path
  - `HEALTH_ENDPOINT` - Health check endpoint
- Auto-fills context from post title/excerpt on single posts
- Supports text selection for focused questions
- Retry logic with exponential backoff for server errors
- Health check disables UI if API unreachable

### Styling System

**SCSS Structure** (`assets/scss/`):
- `style.scss` - Entry point, imports all partials
- `_variables.scss` - CSS custom properties, color schemes, breakpoints
- `_base.scss` - Reset, typography, dark/light mode base styles
- `_layout.scss` - Grid, containers, header, footer, navigation, TOC, **bbPress forum layouts**
- `_components.scss` - Buttons, cards, badges, forms, modals
- `_post.scss` - Single post styles, TOC, related posts, reading time

**Note**: Main navigation styles and table of contents are in `_layout.scss`.

**Additional CSS Files** (`css/`):
- `ai-panel-fixes.css` - AI discussion panel styling fixes
- `bbpress-frontend.css` - Latest bbPress frontend styling (card-based design, dark/light mode)

These are manually maintained and enqueued separately from the Vite build output.

### Theme Customizer Options
Accessible via `get_theme_mod('ailinux_nova_dark_*')`:
- `accent` - Accent color (blue/green)
- `hero_layout` - Homepage layout (grid/list)
- `card_density` - Card spacing (airy/compact)
- `api_base` - AI API base URL

### Custom Image Sizes
Registered in `functions.php`:
- `ailinux-hero`: 1920×1080 (16:9 hero images)
- `ailinux-card`: 1200×675 (16:9 card thumbnails)

### SEO & Schema
Implemented in `functions.php`:
- `ailinux_nova_dark_render_meta_tags()` - OG/Twitter meta tags (priority 10)
- `ailinux_nova_dark_schema_markup()` - BlogPosting JSON-LD (priority 20)
- `ailinux_nova_dark_breadcrumb_schema()` - Breadcrumb list JSON-LD (priority 21)

## bbPress Integration

**Templates** (`bbpress/`):
- `content-single-topic-lead.php` - Topic lead post with breadcrumbs
- `loop-single-reply.php` - Individual reply display
- `loop-topics.php` - Topic list with pagination

**Styling**:
- Forum layout styles compiled into `dist/style.css` (from `_layout.scss`)
- Additional frontend styling in `css/bbpress-frontend.css`

**Optimizations**:
- Forum menu items detected via title matching (functions.php:656-666)
- Swup automatically disabled on forum/topic links to prevent transition issues
- Posts per page increased to 200 for better performance

## Important Development Notes

### Coding Style
**PHP** (WordPress standards):
- Four-space indentation
- Prefix all global functions with `ailinux_nova_dark_` to avoid collisions
- Use `get_template_part()` for reusable template fragments
- Keep templates slim; push logic into `inc/*.php` helpers

**SCSS**:
- Two-space indentation
- BEM-leaning class names (`.block__element--modifier`)
- CSS custom properties defined in `_variables.scss`
- Import partials in `style.scss` entry point

**JavaScript**:
- ES6+ syntax (Vite transpiles for browser compatibility)
- Module pattern (e.g., `AilinuxNovaApp`, `AilinuxNovaTransitions`)
- Respect `prefers-reduced-motion` for animations

### Asset Management
- Assets pre-built in `dist/` - production doesn't need npm
- **Never edit files in `dist/` directly** (auto-generated by Vite)
- Never commit `node_modules/` to version control
- Asset versioning uses file mtime via `ailinux_nova_dark_get_asset_version()`

### Critical Script Loading Order
WordPress enqueues scripts in this specific order (see functions.php):
1. `colorMode.js` - Enqueued in `<head>` with priority 1 (**must be blocking** to prevent FOUC)
2. `app.js` - Main bundle in footer
3. `mobile-menu.js` - Mobile navigation in footer
4. `webgpu.js` - WebGPU support in footer
5. `NOVA_API` - Localized to `app.js` handle (provides API endpoints)

### Performance Considerations
- Reading time assumes 200 WPM (constant in app.js)
- IntersectionObserver respects `prefers-reduced-motion`
- Asset versioning uses file mtime for cache busting
- Menu rendering optimized with caching
- Posts per page: 200 (blog archives/home)

### Mobile & Responsive
- Breakpoints defined in `_variables.scss`
- Mobile menu slides from right with overlay
- Hamburger transforms to X icon
- Body scroll disabled when mobile menu active
- Header scales down to 320px width
- Search/login links hidden on mobile
- AI button compressed to "AI" badge
- Enhanced pagination with jump links (±10, ±25, ±50, ±100 pages)

## WordPress Requirements
- WordPress 5.9+ (for theme.json support)
- PHP 7.4+
- Gutenberg blocks supported via `theme.json`
- Widget areas: `sidebar-1`, `footer-widgets`
- Navigation menus: `primary` (header), `footer`

## Theme Support Features
Registered in functions.php:
- `automatic-feed-links`
- `title-tag`
- `post-thumbnails`
- `responsive-embeds`
- `html5` (comment-form, comment-list, gallery, caption, style, script, navigation-widgets)
- `align-wide`
- `editor-styles` (uses `editor-styles.css`)
- `custom-logo` (240×80, flexible dimensions)

## Known Issues & External Dependencies

See `known-bugs.txt` for details on:
1. Service Worker cache failures (plugin-related, not theme)
2. Assets blocked by browser extensions (`net::ERR_BLOCKED_BY_CLIENT`)
3. Invalid certificate on third-party services (`addtoany.com`)

These are client-side or external issues not fixable in theme code.

## File Structure Reference

```
ailinux-nova-dark-dev/
├── assets/
│   ├── js/          # Source JavaScript (compiled to dist/)
│   └── scss/        # Source SCSS partials (compiled to dist/style.css)
├── bbpress/         # bbPress template overrides
├── css/             # Hand-authored CSS (bypasses build, enqueued separately)
├── dist/            # Built assets (committed, never edit directly)
├── inc/             # PHP helper functions
├── template-parts/  # Reusable PHP template fragments
├── functions.php    # Theme setup, enqueuing, WordPress integration
├── vite.config.js   # Vite build configuration
└── style.css        # Theme header (required by WordPress)
```

## Commit Conventions

Use concise, imperative subjects following this pattern:
- `feat: add hero layout toggle to customizer`
- `fix: prevent mobile menu scroll on iOS Safari`
- `refactor: consolidate navigation overflow logic`
- `style: update button padding for consistency`
- `docs: clarify Vite entry points in CLAUDE.md`

## CSS++ Design Engine (Experimental)

**Status:** Alpha – Multisensory design language integrated into theme

### What is CSS++?

CSS++ is an experimental **multisensory design language** that extends CSS with:
- **Geometry** – Pixel-grid, shapes, depth, 3D primitives
- **Lighting** – Shadows, reflections, glow, light sources
- **Volumetrics** – Fog, particles, bloom, film grain
- **Texture** – Materials (metal, wood, cloth, glass) with PBR properties
- **Audio** – UI sounds, cursor SFX, ambient soundscapes
- **Theme** – Global design system with sensory depth

### Directory Structure

```
csspp/
├── modules/        # Core CSS++ modules (geometry, lighting, etc.)
├── compiler/       # JavaScript compiler (transpiles .csspp → .css)
├── examples/       # Demo files (button-demo.csspp)
├── docs/           # Documentation (README.md, GETTING-STARTED.md)
└── ../csspp-output/  # Compiled output (CSS + JSON assets)
```

### Quick Usage

**Compile example:**
```bash
npm run csspp:example
```

**Output:**
- `csspp-output/button-demo.css` – Standard CSS
- `csspp-output/button-demo.assets.json` – Audio/texture bindings

### Example CSS++ Code

```csspp
.btn-metal {
  /* Geometry */
  shape: rounded-rect(0.5rem);
  depth: 0.2rem;

  /* Material */
  material: brushed-metal(#888888, roughness: 0.3);

  /* Lighting */
  shadow-type: soft;
  reflectivity: 0.6;

  /* Audio */
  hover-sfx: chime(440Hz, decay: 0.2s);
  click-sfx: click(mechanical);
}
```

**Compiles to standard CSS:**
```css
.btn-metal {
  border-radius: 0.5rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  background: linear-gradient(135deg, #e0e0e0, #f0f0f0);
}
```

### Integration Status

- ✅ Core syntax defined
- ✅ 6 modules created (geometry, lighting, volumetrics, texture, audio, theme)
- ✅ JavaScript compiler prototype
- ✅ Example button styles
- ⏳ Vite plugin (planned)
- ⏳ Audio runtime (Web Audio API)
- ⏳ Particle system (Canvas/WebGL)

### Documentation

- **Getting Started:** `csspp/docs/GETTING-STARTED.md`
- **Full Spec:** `csspp/docs/README.md`
- **Modules:** `csspp/modules/*.csspp` (syntax reference)
- **Examples:** `csspp/examples/button-demo.csspp`

### Parallel Development Strategy

CSS++ and WordPress theme evolve **in parallel**:
1. New CSS++ features are tested in the theme
2. Successful patterns flow back into CSS++ spec
3. Theme benefits from innovative design capabilities

**Note:** CSS++ is experimental and not required for theme functionality. It's an optional enhancement layer.

---

## Additional Documentation

- **AGENTS.md** - Development conventions, commit guidelines, testing patterns
- **README.md** - German-language theme overview and installation guide
- **changelog.txt** - Detailed version history
- **known-bugs.txt** - External dependency issues (browser extensions, third-party services)
- **theme.json** - Gutenberg block configuration
- **csspp/docs/** - CSS++ Design Engine documentation
