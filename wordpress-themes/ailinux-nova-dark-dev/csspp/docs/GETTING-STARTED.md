# CSS++ Getting Started Guide

## Quick Start

### 1. Compile Example Button

```bash
npm run csspp:example
```

Dies kompiliert `csspp/examples/button-demo.csspp` und erstellt:
- `csspp-output/button-demo.css` – Standard CSS
- `csspp-output/button-demo.assets.json` – Asset-Definitionen

### 2. Inspect Output

```bash
cat csspp-output/button-demo.css
cat csspp-output/button-demo.assets.json
```

### 3. Use in WordPress Theme

Im `functions.php` einbinden:

```php
// Enqueue compiled CSS++ output
wp_enqueue_style(
  'csspp-buttons',
  get_template_directory_uri() . '/csspp-output/button-demo.css',
  [],
  filemtime(get_template_directory() . '/csspp-output/button-demo.css')
);
```

---

## Create Your First CSS++ File

### Step 1: Create File

```bash
touch csspp/examples/my-component.csspp
```

### Step 2: Write CSS++

```csspp
@import "modules/geometry";
@import "modules/lighting";

.my-card {
  /* Geometry */
  shape: rounded-rect(0.5rem);
  depth: 0.2rem;

  /* Lighting */
  shadow-type: soft;
  light-intensity: 0.7;

  /* Standard CSS */
  padding: 1rem;
  background: #ffffff;
}
```

### Step 3: Compile

```bash
node csspp/compiler/csspp-compiler.js csspp/examples/my-component.csspp
```

Output: `csspp-output/my-component.css`

---

## Module System

### Available Modules

1. **geometry.csspp** – Shapes, Pixel-Grid, Depth, Curves
2. **lighting.csspp** – Shadows, Reflections, Glow, Light Sources
3. **volumetrics.csspp** – Fog, Particles, Bloom, Film Effects
4. **texture.csspp** – Materials, Fabrics, Metals, Woods
5. **audio.csspp** – Sounds, SFX, Ambient Audio
6. **theme.csspp** – Global Design System

### Import Syntax

```csspp
@import "modules/geometry";
@import "modules/lighting";
```

---

## Property Reference

### Geometry

```csspp
shape: circle | polygon(6) | rounded-rect(0.5rem);
pixel-grid: 8x8 | 16x16;
depth: 0.2rem | 3d;
curve: bezier(...);
```

### Lighting

```csspp
light-intensity: 0.7;
shadow-type: soft | hard | contact;
reflectivity: 0.8 | chrome | glass(0.5);
glow-color: #ff00ff;
glow-intensity: 0.6;
```

### Volumetrics

```csspp
fog-density: 0.2;
particle: dust(5%) | rain(30%) | sparks(10%);
bloom-strength: 0.4;
film-grain: 0.3;
```

### Texture

```csspp
material: brushed-metal(#888888, roughness: 0.3);
texture: noise(0.5) | cloth(linen);
roughness: 0.5;
metallic: 0.8;
fabric: linen | silk | leather;
metal: aluminum | gold | chrome;
```

### Audio

```csspp
hover-sfx: chime(440Hz, decay: 0.2s);
click-sfx: click(mechanical);
cursor-move-sfx: cloth-rub(quiet);
ambient-sound: quiet-room(0.1);
```

---

## Theme System

### Define Theme

```csspp
@theme my-theme {
  primary-color: #4466ff;
  accent-color: #ff6644;

  material-style: safe-room;
  texture-preference: rough;

  ui-soundscape: mechanical;
  ambient-light: 0.5;
}
```

### Apply Theme

```html
<div data-theme="my-theme">
  <!-- Content inherits theme -->
</div>
```

---

## Compiler Workflow

```
input.csspp
   ↓
[Preprocessing]
   ↓ (Imports, Theme-Expansion)
[Parsing]
   ↓ (AST-Generation)
[Validation]
   ↓ (Property-Checks)
[Transformation]
   ↓ (CSS++ → CSS)
[Code Generation]
   ↓
output.css + assets.json
```

---

## Integration with WordPress Theme

### Method 1: Pre-Compile (Recommended)

1. Write CSS++ files in `csspp/examples/`
2. Compile: `npm run csspp:compile`
3. Enqueue output in `functions.php`

### Method 2: Build Pipeline Integration

Create Vite plugin (future feature):

```js
// vite.config.js
import cssppPlugin from './csspp/vite-plugin-csspp.js';

export default {
  plugins: [
    cssppPlugin({
      include: 'csspp/**/*.csspp'
    })
  ]
};
```

---

## Examples

### 1. Metallic Button

```csspp
.btn-metal {
  shape: rounded-rect(0.5rem);
  material: brushed-metal(#888888);
  shadow-type: soft;
  hover-sfx: chime(440Hz);
}
```

**Compiles to:**

```css
.btn-metal {
  border-radius: 0.5rem;
  background: linear-gradient(135deg, #e0e0e0 0%, #f0f0f0 50%, #e0e0e0 100%);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}
```

**Assets JSON:**

```json
{
  "audio": {
    ".btn-metal": {
      "hover-sfx": "chime(440Hz)"
    }
  }
}
```

### 2. Neon Glow Effect

```csspp
.neon-text {
  glow-color: #00ffff;
  glow-intensity: 0.8;
  light-response: emissive;
}
```

**Compiles to:**

```css
.neon-text {
  box-shadow: 0 0 20px #00ffff;
  filter: brightness(1.2);
}
```

### 3. Foggy Background

```csspp
.foggy-scene {
  fog-density: 0.2;
  particle: mist(slow);
  color-grade: cool;
}
```

**Note:** Advanced volumetrics require runtime (future feature).

---

## Next Steps

1. **Explore Examples:** Check `csspp/examples/button-demo.csspp`
2. **Read Module Docs:** See `csspp/modules/*.csspp` for syntax reference
3. **Compile & Test:** Use `npm run csspp:example` to see output
4. **Integrate:** Add compiled CSS to theme via `functions.php`
5. **Experiment:** Create your own `.csspp` files!

---

## Roadmap

### Phase 1 (Current)
✅ Core syntax defined
✅ Module system
✅ Basic compiler prototype
✅ Example files

### Phase 2 (Next)
⏳ Vite plugin for auto-compilation
⏳ Audio runtime (Web Audio API)
⏳ Particle system (Canvas/WebGL)
⏳ Texture loader

### Phase 3 (Future)
⏳ AILinux OS integration
⏳ Terminal theme support
⏳ AI-generated themes
⏳ Binary pack format

---

## Help & Support

- **Documentation:** `csspp/docs/README.md`
- **Examples:** `csspp/examples/`
- **Modules:** `csspp/modules/`
- **Compiler:** `csspp/compiler/csspp-compiler.js`

---

## Philosophy

> **"Leicht wie CSS, mächtig wie eine Game-Engine"**

CSS++ ist keine bloated Framework, sondern eine **präzise Erweiterung** von CSS für multisensorisches Design. Es kompiliert zu Standard-CSS wo möglich, und exportiert erweiterte Features als JSON-Assets.

**Deterministisch. Kompilierbar. Elegant.**
