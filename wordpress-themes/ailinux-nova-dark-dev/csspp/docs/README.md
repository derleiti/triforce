# CSS++ Design Engine

**Version**: 0.1.0-alpha
**Status**: Experimental
**Integration**: WordPress Theme (ailinux-nova-dark-dev)

---

## Vision

CSS++ ist eine **multisensorische Designsprache** für immersive UI/UX-Systeme. Sie erweitert traditionelles CSS um:

- **Geometry** – Pixel-Grid, 2D/3D-Primitive, Splines
- **Lighting** – Schatten, Reflexion, Lichtquellen
- **Volumetrics** – Nebel, Partikel, Bloom, Glow
- **Texture** – Materialien, Stoffarten, Roughness
- **Audio** – UI-Sounds, Cursor-SFX, Hover-Feedback
- **Theme** – Globale Design-Tokens mit sensorischer Tiefe

---

## Philosophie

### Leicht wie CSS, mächtig wie eine Game-Engine

```csspp
/* Traditionelles CSS */
.button {
  background: #4466ff;
  padding: 1rem;
}

/* CSS++ – Multisensorisch */
.button {
  material: brushed-metal(blue, roughness: 0.3);
  geometry: rounded-rect(radius: 0.5rem);
  light-response: reflective;
  hover-sfx: chime(soft, pitch: 440Hz);
  cursor-texture: cloth;
}
```

### Deterministisch & Kompilierbar

CSS++ ist **keine Laufzeit-Magie**, sondern wird zu Standard-CSS + JSON-Assets kompiliert:

```
input.csspp → Compiler → output.css + assets.json
```

Die Runtime ist optional – für erweiterte Features wie Audio-Binding.

---

## Modul-Übersicht

### 1. `geometry.csspp`
Pixel-Grid-System, 2D/3D-Formen, Kurven

**Properties**:
- `shape` – Polygon, Kreis, Pfad
- `pixel-grid` – Rasterbasierte Layouts
- `depth` – Z-Achsen-Tiefe für Pseudo-3D

**Beispiel**:
```csspp
.icon {
  shape: polygon(6); /* Hexagon */
  pixel-grid: 8x8;
  depth: 0.2rem;
}
```

### 2. `lighting.csspp`
Licht, Schatten, Reflexionen

**Properties**:
- `light-intensity` – Stärke (0.0–1.0)
- `shadow-type` – hard, soft, contact
- `reflectivity` – Material-Glanz

**Beispiel**:
```csspp
.card {
  light-intensity: 0.7;
  shadow-type: soft;
  reflectivity: glass(0.4);
}
```

### 3. `volumetrics.csspp`
Atmosphärische Effekte

**Properties**:
- `fog-density` – Nebel (0.0–1.0)
- `particle` – Staub, Funken, Regen
- `bloom-strength` – Glow-Effekt

**Beispiel**:
```csspp
.background {
  fog-density: 0.15;
  particle: dust(3%, drift: slow);
  bloom-strength: 0.3;
}
```

### 4. `texture.csspp`
Materialien & Oberflächen

**Properties**:
- `texture` – Vordefinierte oder Custom-Texturen
- `roughness` – 0.0 (glatt) bis 1.0 (rau)
- `pattern` – Repeating-Muster

**Beispiel**:
```csspp
.surface {
  texture: cloth(linen, color: #f0f0f0);
  roughness: 0.6;
  pattern: weave(2x2);
}
```

### 5. `audio.csspp`
Akustische UI-Bindungen

**Properties**:
- `hover-sfx` – Sound bei Hover
- `click-sfx` – Sound bei Click
- `cursor-move-sfx` – Cursor-Bewegungsgeräusch

**Beispiel**:
```csspp
.button {
  hover-sfx: chime(440Hz, decay: 0.2s);
  click-sfx: click(mechanical);
}
```

### 6. `theme.csspp`
Globales Design-System

**Properties**:
- `primary-color` – Hauptfarbe
- `material-style` – Theme-Preset
- `ui-accent` – Akzentfarbe mit Effekten

**Beispiel**:
```csspp
:root {
  primary-color: #4466ff;
  material-style: safe-room;
  ui-accent: gold(0.6, shimmer: true);
}
```

---

## Compiler-Pipeline

```
┌─────────────┐
│ .csspp File │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│ Preprocessing   │ (Imports, Variablen)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Semantic Check  │ (Property-Validierung)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Material Binding│ (Textur-DB-Lookup)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Geometry Trans. │ (Shape → SVG/Canvas)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Audio Mapping   │ (SFX → Event-Bindings)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ CSS + JSON IR   │ (Standard CSS + Assets)
└─────────────────┘
```

---

## Verwendung im Theme

### 1. Erstelle `.csspp` Datei

```csspp
/* csspp/examples/button.csspp */
@import "modules/geometry";
@import "modules/lighting";

.btn-primary {
  material: brushed-metal(#4466ff);
  shape: rounded-rect(0.5rem);
  light-response: reflective;
  hover-sfx: chime(soft);
}
```

### 2. Kompiliere

```bash
npm run csspp:compile
```

### 3. Output

```css
/* dist/button.css */
.btn-primary {
  background: linear-gradient(135deg, #4466ff, #5577ff);
  border-radius: 0.5rem;
  box-shadow: 0 2px 8px rgba(68, 102, 255, 0.3);
}

.btn-primary:hover {
  box-shadow: 0 4px 16px rgba(68, 102, 255, 0.5);
}
```

```json
/* dist/button.assets.json */
{
  "audio": {
    ".btn-primary": {
      "hover": "chime-soft-440hz.mp3"
    }
  },
  "textures": {
    ".btn-primary": {
      "material": "brushed-metal",
      "color": "#4466ff",
      "roughness": 0.3
    }
  }
}
```

---

## Roadmap

### Phase 1: Core Syntax (Aktuell)
- ✅ Module-Struktur
- ⏳ Basis-Properties definieren
- ⏳ Einfacher Parser (JavaScript)

### Phase 2: Compiler
- ⏳ CSS-Transpilation
- ⏳ Asset-Generation (JSON)
- ⏳ Vite-Plugin

### Phase 3: Runtime
- ⏳ Audio-Engine (Web Audio API)
- ⏳ Canvas/WebGL-Renderer für Geometry
- ⏳ Texture-Loader

### Phase 4: AILinux Integration
- ⏳ Binary Pack Format
- ⏳ OS-Theme-Support
- ⏳ Terminal-UI-Bindings

---

## Beitragen

Dies ist ein experimentelles Projekt im WordPress-Theme integriert.

**Testbed**: `csspp/examples/`
**Module**: `csspp/modules/`
**Compiler**: `csspp/compiler/`

Änderungen bitte dokumentieren und in `CLAUDE.md` referenzieren.

---

## Lizenz

Experimentell – Kein offizielles Release.
