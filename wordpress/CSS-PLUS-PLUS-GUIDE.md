# 🎨 CSS++ Design Engine - Complete Integration Guide

**Version:** 1.0.0
**Created:** 2025-01-25
**Status:** Production Ready

---

## 📋 What is CSS++?

**CSS++** is an experimental **multisensory design language** that extends CSS with:

- **Geometry** - Shapes, pixel-grid, depth, 3D primitives
- **Lighting** - Shadows, reflections, glow, light sources
- **Volumetrics** - Fog, particles, bloom, film grain
- **Texture** - Materials (metal, wood, cloth, glass) with PBR properties
- **Audio** - UI sounds, cursor SFX, ambient soundscapes
- **Theme** - Global design system with sensory depth

### How it Works

1. Write `.csspp` files with extended properties
2. Vite Plugin compiles to standard CSS + JSON assets
3. WordPress enqueues compiled CSS automatically
4. Optional: Runtime loads audio bindings for interactive sounds

---

## 📁 Project Structure

```
/home/zombie/wordpress/html/wp-content/themes/ailinux-nova-dark/
├── csspp/
│   ├── modules/              # Core CSS++ modules
│   │   ├── geometry.csspp    # Shapes, depth, 3D
│   │   ├── lighting.csspp    # Shadows, glow, reflections
│   │   ├── texture.csspp     # Materials, PBR properties
│   │   ├── audio.csspp       # UI sounds, SFX
│   │   ├── volumetrics.csspp # Particles, fog, bloom
│   │   └── theme.csspp       # Design system definitions
│   ├── examples/             # Demo files
│   │   └── button-demo.csspp # Full button examples
│   └── compiler/             # Standalone compiler
│       └── csspp-compiler.js # Node.js compiler
├── csspp-output/             # Build output
│   ├── *.css                 # Compiled CSS
│   ├── csspp-assets.json     # Audio/texture bindings
│   └── csspp-runtime.js      # Web Audio API runtime
├── inc/
│   └── csspp-integration.php # WordPress integration
└── vite-plugin-csspp.js      # Vite build plugin
```

---

## 🚀 Quick Start

### Step 1: Install & Setup

Theme already contains CSS++ files. No installation needed!

### Step 2: Write CSS++

**Create:** `csspp/examples/my-button.csspp`

```csspp
.btn-metal {
  /* Geometry */
  shape: rounded-rect(0.5rem);
  depth: 0.2rem;

  /* Material */
  material: brushed-metal(#888888, roughness: 0.3);
  metallic: 0.8;

  /* Lighting */
  light-intensity: 0.7;
  shadow-type: soft;
  reflectivity: 0.6;

  /* Audio */
  hover-sfx: chime(440Hz, decay: 0.2s);
  click-sfx: click(mechanical);

  /* Standard CSS */
  padding: 0.75rem 1.5rem;
  font-weight: 600;
  cursor: pointer;
}
```

### Step 3: Import in Vite

**Edit:** `vite.config.js`

```javascript
import cssppPlugin from './vite-plugin-csspp.js';

export default defineConfig({
  plugins: [
    cssppPlugin({
      include: /\.csspp$/,
      outputDir: 'csspp-output',
      generateAssets: true
    })
  ],
  build: {
    rollupOptions: {
      input: {
        // ... existing entries
        'my-button': resolve(__dirname, 'csspp/examples/my-button.csspp')
      }
    }
  }
});
```

### Step 4: Build

```bash
cd html/wp-content/themes/ailinux-nova-dark
npm run build
```

**Output:**
- `csspp-output/my-button.css` - Standard CSS
- `csspp-output/csspp-assets.json` - Audio bindings

### Step 5: Enqueue in WordPress

**Edit:** `functions.php`

```php
// Load CSS++ Integration
require_once get_template_directory() . '/inc/csspp-integration.php';
```

**Or manually enqueue:**

```php
function my_theme_enqueue_csspp() {
    wp_enqueue_style(
        'my-button-csspp',
        get_template_directory_uri() . '/csspp-output/my-button.css',
        array(),
        filemtime(get_template_directory() . '/csspp-output/my-button.css')
    );
}
add_action('wp_enqueue_scripts', 'my_theme_enqueue_csspp');
```

---

## 🎯 CSS++ Syntax Reference

### Geometry

```csspp
/* Shapes */
shape: circle;
shape: square;
shape: polygon(6);                    /* Hexagon */
shape: rounded-rect(0.5rem);

/* Pixel Grid */
pixel-grid: 16x16;                    /* Retro 16x16 grid */
pixel-grid: 8;                        /* Shorthand for 8x8 */

/* Depth */
depth: 0.3rem;                        /* Pseudo-3D depth */
depth: 3d;                            /* Enable CSS 3D transforms */

/* Border Shape */
border-shape: polygon(6);             /* Hexagonal border */
```

### Lighting

```csspp
/* Shadows */
shadow-type: soft;                    /* 0 4px 12px rgba(0,0,0,0.15) */
shadow-type: hard;                    /* 0 2px 4px rgba(0,0,0,0.3) */
shadow-type: contact;                 /* 0 1px 2px rgba(0,0,0,0.2) */

/* Glow */
glow-color: #00ffff;
glow-intensity: 0.8;
glow-radius: 1.5rem;

/* Light Response */
light-intensity: 0.7;                 /* 0.0 - 1.0 */
reflectivity: 0.6;
```

### Texture & Materials

```csspp
/* Materials */
material: brushed-metal(#888888, roughness: 0.3);
material: glass(0.3);
material: plastic(glossy, #000000);

/* Properties */
metallic: 0.8;                        /* 0.0 - 1.0 */
roughness: 0.4;                       /* 0.0 - 1.0 */

/* Textures */
texture: wood-grain(oak, scale: 1.5);
texture: cloth(linen, color: #e8d5c4);
```

### Audio (Interactive)

```csspp
/* UI Sounds */
hover-sfx: chime(440Hz, decay: 0.2s);
click-sfx: click(mechanical);
cursor-move-sfx: cloth-rub(quiet);

/* Ambient */
ambient-sound: quiet-room(0.05);
```

### Volumetrics

```csspp
/* Particles */
particle: sparks(2%) from center on click;

/* Atmospheric */
fog-density: 0.05;
bloom-strength: 0.5;
film-grain: 0.1;
```

### Theme Definitions

```csspp
@theme button-safe-room {
  primary-color: #4a5568;
  accent-color: #d4af37;
  material-style: vintage-industrial;
  texture-preference: rough;
  interaction-sounds: mechanical;
}

.btn-group[data-theme="safe-room"] .btn {
  material: var(--theme-material-style);
  hover-sfx: gear(light);
}
```

---

## 🔧 Vite Plugin Configuration

The **`vite-plugin-csspp.js`** automatically:

1. Detects `.csspp` files
2. Compiles to standard CSS
3. Extracts audio bindings to JSON
4. Generates `csspp-assets.json`
5. Supports HMR (Hot Module Replacement)

**Full Config:**

```javascript
import cssppPlugin from './vite-plugin-csspp.js';

export default defineConfig({
  plugins: [
    cssppPlugin({
      include: /\.csspp$/,          // File pattern
      outputDir: 'csspp-output',    // Output directory
      generateAssets: true          // Generate JSON assets
    })
  ]
});
```

---

## 🎵 Audio Runtime (Optional)

The **CSS++ Runtime** loads audio bindings and plays sounds on interaction.

### Enable Runtime

**In WordPress Customizer:**
- Navigate to: **Appearance → Customize → CSS++ Features**
- Enable: **"Audio Runtime aktivieren"**

**Manual Activation:**

```php
// In functions.php
add_filter('theme_mod_csspp_runtime_enabled', '__return_true');
```

### How It Works

1. Runtime reads `csspp-assets.json`
2. Binds audio events to DOM elements
3. Uses Web Audio API to synthesize sounds
4. Respects `prefers-reduced-motion`

**Example:**

```csspp
.btn-beep {
  hover-sfx: chime(440Hz, decay: 0.2s);
  click-sfx: pop(0.6);
}
```

Runtime automatically:
- Plays 440Hz chime on hover
- Plays pop sound on click
- Throttles cursor-move sounds to 100ms

---

## 🔄 Integration with Cache-Busting

CSS++ works seamlessly with the improved cache-busting system:

**Step 1:** Update `vite.config.improved.js` to include CSS++ plugin

```javascript
import cssppPlugin from './vite-plugin-csspp.js';
import { wordpressManifestPlugin } from './vite.config.improved.js';

export default defineConfig({
  plugins: [
    cssppPlugin(),
    wordpressManifestPlugin()
  ],
  build: {
    rollupOptions: {
      input: {
        // Standard entries
        app: resolve(__dirname, 'assets/js/app.js'),
        style: resolve(__dirname, 'assets/scss/style.scss'),

        // CSS++ entries
        'button-demo': resolve(__dirname, 'csspp/examples/button-demo.csspp')
      }
    }
  }
});
```

**Step 2:** Assets get hash-based names

```
dist/button-demo.abc123.css
dist/csspp-assets.abc123.json
```

**Step 3:** WordPress Asset-Loader enqueues with hashes

```php
Ailinux_Nova_Dark_Asset_Loader::enqueue_style(
    'button-demo-csspp',
    'button-demo',    // Asset name in manifest
    'button-demo.css' // Fallback
);
```

---

## 📊 Compilation Process

### Phase 1: Preprocessing
- Resolve `@import` statements
- Expand `@theme` definitions into CSS variables

### Phase 2: Parsing
- Tokenize CSS++ syntax
- Build AST (Abstract Syntax Tree)

### Phase 3: Validation
- Check property values
- Validate syntax
- Emit warnings for invalid values

### Phase 4: Transformation
- Convert CSS++ properties to standard CSS:
  - `shape: circle` → `border-radius: 50%`
  - `shadow-type: soft` → `box-shadow: 0 4px 12px...`
  - `glow-color: #00ffff` → `box-shadow: 0 0 20px #00ffff`

### Phase 5: Code Generation
- Generate standard CSS output
- Extract audio/texture bindings to JSON

### Phase 6: Output
- Write `.css` file
- Write `.assets.json` file

---

## 🧪 Examples & Demos

### Example 1: Metallic Button

```csspp
.btn-metal {
  shape: rounded-rect(0.5rem);
  depth: 0.2rem;
  material: brushed-metal(#888888, roughness: 0.3);
  shadow-type: soft;
  hover-sfx: chime(440Hz, decay: 0.2s);
  padding: 0.75rem 1.5rem;
}
```

**Compiles to:**

```css
.btn-metal {
  border-radius: 0.5rem;
  box-shadow: 0 0.2rem 0.4rem rgba(0, 0, 0, 0.15);
  background: linear-gradient(135deg, #e0e0e0 0%, #f0f0f0 50%, #e0e0e0 100%);
  padding: 0.75rem 1.5rem;
}
```

### Example 2: Glass Card

```csspp
.card-glass {
  shape: rounded-rect(0.75rem);
  material: glass(0.3);
  transparency: frosted(8px);
  shadow-type: soft;
  backdrop-filter: blur(10px);
}
```

### Example 3: Neon Button

```csspp
.btn-neon {
  shape: rounded-rect(0.25rem);
  glow-color: #00ffff;
  glow-intensity: 0.8;
  particle: sparks(2%) from center on click;
  hover-sfx: whoosh(up);
  border: 2px solid #00ffff;
}
```

---

## 📝 Responsive & Accessibility

### Responsive Adjustments

```csspp
@media (max-width: 768px) {
  .btn-metal {
    padding: 0.5rem 1rem;
    font-size: 0.875rem;
  }

  /* Reduce particle effects on mobile */
  .btn-neon {
    particle: none;
  }
}
```

### Accessibility

```csspp
@media (prefers-reduced-motion: reduce) {
  * {
    hover-sfx: none;
    click-sfx: none;
    particle: none;
    texture-animation: none;
  }
}

@media (prefers-color-scheme: dark) {
  .btn-cloth {
    texture: cloth(linen, color: #2d3748);
    color: #e2e8f0;
  }
}
```

---

## 🐛 Troubleshooting

### Problem: CSS++ not compiling

**Symptom:** `.csspp` files not generating `.css` output

**Solution:**
```bash
# 1. Check Vite plugin is loaded
grep -n "cssppPlugin" vite.config.js

# 2. Rebuild
npm run build

# 3. Check output directory
ls -la csspp-output/
```

### Problem: Audio not playing

**Symptom:** No sounds on hover/click

**Solution:**
1. Enable Runtime in Customizer
2. Check browser console for errors
3. Verify `csspp-assets.json` exists
4. User must interact with page first (Web Audio API requirement)

### Problem: Manifest not updating

**Symptom:** Changes not reflected after build

**Solution:**
```bash
# Clear dist/ and rebuild
rm -rf dist/*
npm run build

# Clear WordPress cache
docker compose run --rm -u www-data wpcli wp cache flush
```

---

## 📚 Additional Resources

- **Full Compiler Source:** `csspp/compiler/csspp-compiler.js`
- **Module Reference:** `csspp/modules/*.csspp`
- **WordPress Integration:** `inc/csspp-integration.php`
- **Runtime Source:** `csspp-output/csspp-runtime.js`
- **Vite Plugin:** `vite-plugin-csspp.js`

---

## ✅ Next Steps

1. **Try the Button Demo:**
   ```bash
   npm run build
   # Open WordPress site, inspect `.btn-metal` elements
   ```

2. **Create Your Own:**
   - Write `.csspp` file in `csspp/examples/`
   - Add to Vite config
   - Build and test

3. **Enable Audio:**
   - Customizer → CSS++ Features → Enable Runtime
   - Test interactive sounds

4. **Integrate with Cache-Busting:**
   - Follow UPGRADE-GUIDE.md for Vite improvements
   - CSS++ works automatically with hashed assets

---

**Created:** 2025-01-25
**Version:** 1.0.0
**Status:** ✅ Production Ready

*CSS++ - Multisensory Design for the Modern Web*
