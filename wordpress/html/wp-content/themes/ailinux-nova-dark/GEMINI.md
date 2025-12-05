# GEMINI – Analysis & Fix Plan (canonical)

## Scope
Analyze the WordPress theme **Ailinux Nova Dark**. Detect concrete issues, provide exact patches (diffs), and propose a cleanup list (files/blocks to remove). Keep it factual and testable.

## Status: Verified & Improved (2025-10-05)
All canonical fixes from the original plan have been verified as implemented. The following improvements have been added:
- **feat**: Add CSP nonce support for theme scripts.
- **fix(ai)**: Implement robust fetch handling, an API health check, and a disabled UI state.
- **chore(bbpress)**: Enforce `data-no-swup` on all forum links to prevent transition conflicts.
- **fix(swup)**: Added a micro-debounce to the `page:view` hook for smoother transitions.

## Canonical Fixes (Verified)
1.  **Early Color Mode**: `dist/colorMode.js` is enqueued in `<head>` with priority 1.
2.  **Single `app.js` Enqueue**: The main `dist/app.js` bundle is loaded only once.
3.  **`NOVA_API` Localization**: API endpoints and settings are correctly passed to the client via `wp_localize_script`.
4.  **bbPress Styles**: The theme correctly enqueues `css/bbpress-frontend.css` and the legacy `css/bbpress.css` has been removed.
5.  **Vite I/O**: `vite.config.js` uses the correct entry points and generates un-hashed filenames.

## Improvements Added

### 1. CSP/Nonce Readiness
A filter has been added to `functions.php` to automatically apply a `nonce` attribute to theme scripts if `AILINUX_CSP_NONCE` is defined. This enhances security by allowing strict Content Security Policies.

```php
// functions.php
// Optional CSP nonce support: define AILINUX_CSP_NONCE via server or mu-plugin.
add_filter('script_loader_tag', function ($tag, $handle, $src) {
    if (!defined('AILINUX_CSP_NONCE') || !AILINUX_CSP_NONCE) return $tag;
    $handles = [
        'ailinux-nova-dark-color-mode',
        'ailinux-nova-dark-app',
        'ailinux-nova-dark-mobile-menu',
        'ailinux-nova-dark-customizer',
    ];
    if (in_array($handle, $handles, true)) {
        $tag = str_replace('<script ', '<script nonce="' . esc_attr(AILINUX_CSP_NONCE) . '" ', $tag);
    }
    return $tag;
}, 10, 3);
```

### 2. Robust AI Panel Networking
The "Discuss with AI" feature now has:
*   **API Health Check**: It pings a `/health` endpoint on load. If the API is down, the button is disabled with a helpful tooltip.
*   **Safe JSON Parsing**: Network responses are parsed safely, preventing crashes on invalid JSON.
*   **Clearer Error Messages**: Users now see more specific error messages for network, server, or API-related issues.
*   **CORS Patch Applied**: The backend API server has been updated with the necessary CORS headers to allow cross-origin requests.

### 3. Swup Transition Hardening
*   **bbPress/Forum Links**: All links pointing to forum sections are now automatically marked with `data-no-swup` to ensure they trigger a full page load, avoiding conflicts.
*   **Debounced Init**: A `requestAnimationFrame` debounce has been added to the `page:view` hook to prevent re-initialization jank during rapid navigation.

## Cleanup (Verified)
- Legacy `css/bbpress.css` is deleted.
- No duplicate script enqueues were found.
- `.gitignore` correctly ignores `node_modules/` and `*.map` files.

## Manual Test Plan
1.  **Hard Reload**: Use Ctrl+F5. Confirm the color scheme is correct on first paint (no flash of unstyled content).
2.  **Navigation**: Click 3-4 internal links. Verify smooth transitions and check the browser console for errors.
3.  **AI Panel**:
    *   **API Online**: Open the panel, load models, send a prompt, and confirm you get a response.
    *   **API Offline**: (Simulate by changing the API URL). Confirm the button is disabled and shows a tooltip.
4.  **Forums**: Navigate to a bbPress forum page. Confirm that links within the forum trigger a full page reload, not a Swup transition.
5.  **Customizer**: Open the Customizer, change a theme color, and verify the change appears in the live preview and persists after saving.

## Known Issues Documentation
A `known-bugs.txt` file has been added to the theme to document common console errors that originate from third-party plugins (e.g., Complianz GDPR, AddToAny), browser extensions (ad-blockers), or external service issues. This provides a reference for developers to distinguish between theme bugs and external factors.

## UX & Readability Improvements (2025-10-06)
- **Typography & Rhythm**: Content width adjusted to `68ch` for better readability. Line height and paragraph spacing have been refined for a calmer reading experience.
- **Image Ratios / CLS**: Featured images now have a fixed 16:9 aspect ratio to prevent layout shifts.
- **Resource Hints & Preload**: Added preconnect hints for Google Fonts and a preload for the main stylesheet to improve perceived performance.
- **Navigation Ergonomics**: Increased the size of click targets in the main navigation and improved the visibility of focus states.
- **Sticky Table of Contents**: The table of contents in single posts is now sticky, making it easier to navigate long articles.
- **Forum Wayfinding**: Added a "back to overview" link in bbPress topics.
- **Cleanup**: Removed a redundant `header.php` file.