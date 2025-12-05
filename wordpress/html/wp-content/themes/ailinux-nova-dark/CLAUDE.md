# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Theme Overview

This is **Ailinux Nova Dark**, a modern WordPress theme with a dark-first design inspired by ChatGPT's aesthetic. The theme features generous whitespace, smooth Swup page transitions, an integrated AI discussion panel, and full bbPress forum integration.

## Working Directory Context

The default working directory is `/root/wordpress/html/wp-content/themes/ailinux.me/` - this is the complete theme folder.

Structure:
- `ailinux-nova-dark/` - Main theme directory with all source files, build configuration, and assets
- Root-level redirect files for WordPress theme structure

**Always navigate to `ailinux-nova-dark/` subdirectory for theme development work.**

## Development Commands

### Build & Development
```bash
cd ailinux-nova-dark
npm install                 # Install dependencies
npm run dev                # Start Vite dev server with HMR
npm run build              # Build production assets to dist/
npm run preview            # Preview production build locally
npm run format             # Format JS/SCSS/CSS with Prettier
```

### Theme Packaging
```bash
# Create installable ZIP (excludes node_modules and .git)
zip -r ailinux-nova-dark.zip ailinux-nova-dark -x "*/node_modules/*" "*/.git/*"
```

## Architecture

### Build System
- **Vite** handles the build pipeline (configured in `vite.config.js`)
- Source files in `assets/js/` and `assets/scss/` compile to `dist/`
- Output files have static names (no hashes) for WordPress compatibility
- Entry points: `app.js`, `colorMode.js`, `customizer.js`, `mobile-menu.js`, `style.scss`
- Note: Latest build uses `colorMode.js` (camelCase), not `color-mode.js`

### Key WordPress Integration Points
- **functions.php**: Theme setup, asset enqueuing, customizer settings, schema markup
- Constants: `AILINUX_NOVA_DARK_VERSION`, `AILINUX_NOVA_DARK_DIR`, `AILINUX_NOVA_DARK_URI`
- Asset versioning uses file modification time via `ailinux_nova_dark_get_asset_version()`
- AI API configuration via theme customizer (default: `https://api.ailinux.me:9000`)

### Template Structure
- Standard WordPress template hierarchy in root (`index.php`, `single.php`, `archive.php`, etc.)
- Reusable components in `template-parts/`:
  - `content-hero.php` - Featured post display
  - `content-card.php` - Blog post cards
  - `content-single.php` - Single post content
  - `related-posts.php` - Related posts section
  - `pagination.php` - Custom pagination

### JavaScript Architecture

**Entry Points** (configured in `vite.config.js`):
- `app.js` - Main application logic
- `color-mode.js` - Color mode initialization (blocking, prevents FOUC)
- `customizer.js` - WordPress Customizer live preview
- `mobile-menu.js` - Mobile navigation panel

**app.js Structure**:
- **AilinuxNovaApp**: Main app module with initialization logic
  - Header scroll behavior (sticky, hide on scroll down)
  - Navigation overflow handling (responsive "More" menu)
  - Reading time calculation (200 WPM)
  - Intersection Observer for fade-in animations
  - Table of Contents generation for H2/H3 headings
  - Smooth scroll for anchor links
  - AI Discussion panel integration

- **AilinuxNovaTransitions**: Swup integration for page transitions
  - Re-initializes app on page change
  - Manages `#swup` container transitions

**mobile-menu.js**:
- Handles mobile navigation toggle (`#mobile-menu-toggle`)
- Manages overlay and slide-in panel (`#mobile-nav-panel`)
- Submenu expansion for `.menu-item-has-children`

### AI Discussion Feature
- Floating panel triggered by `#ai-discuss-btn`
- Fetches from configurable API endpoint (NOVA_API.BASE + NOVA_API.CHAT_ENDPOINT)
- Auto-fills context from post title/excerpt on single posts
- Supports text selection for focused questions
- Retry logic with exponential backoff for server errors

### Styling System

**SCSS Modules** in `assets/scss/`:
- `style.scss` - Main entry point, imports all partials
- `_variables.scss` - CSS custom properties, color schemes
- `_base.scss` - Reset, typography, dark/light mode
- `_layout.scss` - Grid, containers, header, footer (includes bbPress forum layouts)
- `_components.scss` - Buttons, cards, badges, forms
- `_post.scss` - Single post styles, TOC, related posts
Note: Some layout-related styles, like the main navigation and table of contents, are located in _layout.scss.

**Additional CSS Files** in `css/`:
- `ai-panel-fixes.css` - AI discussion panel styling fixes
- `bbpress-theme.css` - Comprehensive bbPress forum styling (dark/light mode)
- `bbpress-frontend.css` - Latest bbPress frontend card-based design (Oct 4)
- `bbpress.css` - Legacy bbPress styles (can be removed)

Note: Vite compiles `assets/scss/` to `dist/style.css`; the `css/` directory contains manually maintained stylesheets enqueued separately. The latest bbPress styles are in `bbpress-frontend.css`.

### Theme Customizer Options
Accessible via `ailinux_nova_dark_*` theme mods:
- `ailinux_nova_dark_accent` - Accent color (blue/green)
- `ailinux_nova_dark_hero_layout` - Homepage layout (grid/list)
- `ailinux_nova_dark_card_density` - Card spacing (airy/compact)
- `ailinux_nova_dark_api_base` - AI API base URL

### Color Mode System
- `color-mode.js` runs immediately (blocking) to prevent FOUC
- Reads `localStorage.getItem('color-mode')` or `prefers-color-scheme`
- Sets `data-color-mode="dark|light"` on `<html>`
- Toggle implementation in main app.js

### Custom Image Sizes
- `ailinux-hero`: 1920×1080 (hero images)
- `ailinux-card`: 1200×675 (card thumbnails)

### SEO & Schema
All handled in functions.php:
- `ailinux_nova_dark_render_meta_tags()` - OG/Twitter meta tags
- `ailinux_nova_dark_schema_markup()` - BlogPosting JSON-LD
- `ailinux_nova_dark_breadcrumb_schema()` - Breadcrumb list JSON-LD

## WordPress Context
- This is a **standalone theme** at `/wp-content/themes/ailinux.me/ailinux-nova-dark/`
- Parent directory (`ailinux.me/`) contains minimal redirect files for WordPress compatibility
- Theme requires WordPress 5.9+ for theme.json support
- Gutenberg blocks supported via `theme.json` configuration
- Widget areas: `sidebar-1` (sidebar) and `footer-widgets`
- Navigation menus: `primary` (header) and `footer`

## bbPress Integration

The theme includes complete bbPress forum support:

**Templates** in `bbpress/`:
- `loop-forums.php` - Forum list display
- `loop-topics.php` - Topic list display
- `loop-single-reply.php` - Individual reply display
- `content-single-topic-lead.php` - Topic lead post

**Main Integration**:
- `bbpress.php` - Main bbPress template file in theme root
- Forum styles integrated in `_layout.scss` (compiled to `dist/style.css`)
- Additional standalone styling in `css/bbpress-theme.css`
- Functions in `functions.php` handle bbPress-specific enqueuing and customizations

## Important Notes
- Assets are pre-built in `dist/` - production sites don't need npm
- Never commit `node_modules/` to version control
- Color mode toggle must be blocking to prevent flash
- Swup container ID must be `#swup` for transitions to work
- API endpoint configurable but defaults to `https://api.ailinux.me:9000`
- Mobile menu uses separate `mobile-menu.js` entry point
- Reading time calculation assumes 200 words per minute (WPM constant)

## Performance Optimizations
- bbPress forum links use cached slug lookups to avoid repeated function calls
- `data-no-swup` attribute automatically added to forum links to prevent transition issues
- Menu rendering optimized with static caching for better performance
- Asset versioning based on file modification time for efficient cache busting
- Posts per page set to 200 for blog archives and home page

## Mobile & Responsive Design
- Mobile menu slides in from right side with smooth animation
- Hamburger icon transforms to X when menu is open
- Body scroll disabled when mobile menu is active
- Responsive header scaling for smartphones (down to 320px width)
- Search and login links hidden on mobile to save space
- AI button compressed to "AI" badge on small screens
- Mobile menu button prominently styled with accent color
- Enhanced pagination with quick-jump links (±10, ±25, ±50, ±100 pages)
- Pagination fully responsive with adjusted sizing for mobile devices

## Consent Management & Footer Integration

The theme integrates with Complianz GDPR plugin and includes custom optimizations:

### Consent Banner Styling
External CSS file enqueued by theme: `wp-content/uploads/ailx/consent.css`
- Bold primary accept button for clear call-to-action
- Consistent 8px border-radius on all buttons
- Backdrop blur effect for modern appearance
- Accessible link styling with proper underline-offset
- Auto-loaded with priority 35 (after theme styles)

**Implementation**: `functions.php:725-733` - `ailinux_nova_dark_enqueue_consent_css()`

### Footer Legal Links
Location: `footer.php:19-41`

Three required legal links automatically added to footer:
1. **Datenschutzerklärung** - Pulled from WordPress Privacy Policy page setting
2. **Einwilligungen verwalten** - Complianz consent dialog trigger (class: `cmplz-manage-consent`)
3. **Impressum** - Legal notice from `/impressum/` page (if exists)

**Styling**: Flexbox layout, centered, responsive
- Desktop: Horizontal layout with 1.5rem gaps
- Mobile: Vertical layout for better readability
- Opacity transitions on hover/focus for accessibility

### Navigation Overflow Menu Fix
- Fixed "Mehr v" to "Mehr ▼" (proper Unicode down arrow)
- Location: `assets/js/app.js:130` (source) / `dist/app.js` (built)
- Automatically manages overflow menu items with responsive behavior

## Recent Updates

### 2025-10-06 (UX & Readability)
- feat(UX): Improve readability and navigation ergonomics.
- fix(CLS): Prevent layout shift on hero images by enforcing aspect ratio.
- perf(fonts): Add resource hints to preconnect to Google Fonts.
- style: Refine typography for better reading rhythm.
- style: Make table of contents sticky for easier navigation in long posts.
- style: Improve focus visibility on navigation elements.
- fix(bbpress): Add a 'back to overview' link in topics.
- chore: Remove redundant header.php file.
- chore: Rebuild theme assets via npm run build.

### 2025-10-06 (Documentation & Testing)
- Comprehensive documentation review and validation
- Verified theme documentation matches current implementation
- Confirmed theme assets properly built and deployed
- Validated integration with WordPress 6.8.1 and PHP 8.3
- All theme functionality tested and operational

### 2025-10-05 (Consent & Footer)
- Added consent banner CSS optimizations (`ailx/consent.css`)
- Implemented footer legal links with responsive design
- Fixed navigation overflow button with proper Unicode arrow (▼)
- Rebuilt assets via `npm run build`

### Integration Notes
- Consent styling works with Complianz GDPR (no plugin modifications needed)
- Footer links adapt to WordPress settings (Privacy Page, custom Impressum page)
- MU-plugins handle German translations (see root-level CLAUDE.md)
- Theme version 1.0.6 includes documentation and testing updates
