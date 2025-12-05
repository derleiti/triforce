# Ailinux Nova Dark

Ein modernes, dunkles WordPress-Theme mit ruhigem ChatGPT-inspiriertem Look, grosszuegigem Weissraum und nahtlosen Swup-Seitenuebergaengen. Optimiert fuer hochwertige Tech- und AI-Blogs.

## Features
- Dunkles Grunddesign mit Light-Mode-Toggle (Dark als Standard), automatische `prefers-color-scheme`-Erkennung
- Sticky Navigation mit Scroll-Hide, aktive Sektionen, Skip-Link und sichtbaren Focus-Ringen
- Startseite mit Hero-Highlight (Sticky Post oder neuester Beitrag) plus responsives Grid mit grossen Thumbnails
- Automatische Lesezeitberechnung, sanfte Fade-Up-Animationen (IntersectionObserver respektiert `prefers-reduced-motion`)
- Swup-basierte Seitenuebergaenge, eigene Mini-Implementation (`dist/swup.min.js`) fuer sanfte Fade-Transitions
- Gutenberg-kompatibel: eigene `theme.json`, dunkle Editor-Styles, Wide/Full-Align Support
- Schema.org JSON-LD fuer BlogPosting und Breadcrumbs, OG-/Twitter-Metadaten ohne Plugin
- Build-Pipeline via Vite (SCSS -> CSS, ESBuild-Minifizierung), fertig gebaute Assets in `dist/`

## Installation
1. Repository/Ordner `ailinux-nova-dark/` nach `wp-content/themes/` kopieren oder zippen und ueber das WordPress-Backend hochladen.
2. Im Backend unter **Design -> Themes** aktivieren.
3. Empfohlene Seiteneinstellungen: Startseite auf "Neueste Beitraege" belassen.
4. Menues unter **Design -> Menues** fuer die Positionen "Primary" und "Footer" zuweisen.
5. Unter **Design -> Customizer -> Website-Informationen** Logo/Favicon setzen.

### NPM-Befehle
```bash
npm install
npm run dev    # Entwicklungsserver (Vite) mit HMR
npm run build  # Produktion: kompiliert CSS/JS nach dist/, minifiziert Assets
```
> Hinweis: Die ausgelieferte Variante enthaelt bereits gebaute Assets in `dist/`. Der Build-Verlauf erzeugt keine Hash-Dateien, damit WordPress immer auf `dist/style.css` und `dist/app.js` zugreift.

## Customizer-Optionen
- **Primary Accent**: Umschalter zwischen Blau und Gruen (`accent-blue`, `accent-green`)
- **Hero Layout**: Grid- oder Listen-Layout fuer die Blog-Uebersicht nach dem Hero
- **Blog Card Density**: "Airy" (Standard) oder "Compact" fuer dichtere Karten
- **Logo & Favicon**: Standards des Customizers

## Empfohlene Mediengroessen
- Hero-/Featured-Bild: 1920x1080 px (16:9)
- Post Card Thumbnails: 1200x675 px (16:9)
- SVG/PNG Logos mit transparente Variante fuer Dark/Light Mode

## Verzeichnishinweise
- `assets/scss/` - modulare SCSS-Struktur (`_variables`, `_layout`, ...)
- `assets/js/` - Quell-JavaScript (App-Logik, Farbmodus, Customizer)
- `dist/` - gebaute Produktionsdateien (`style.css`, `app.js`, `swup.min.js`, ...)
- `template-parts/` - Hero-, Card-, Single-Templates, Pagination, Related Posts

## Performance & A11y
- Alle Bilder und iframes nutzen `loading="lazy"`, feste Ratio-Container vermeiden CLS
- IntersectionObserver & Animationen respektieren `prefers-reduced-motion`
- Fokus-Styles, Skip-Link, ARIA-Labels und sichtbare States fuer Tastaturnavigation
- Lesezeitberechnung (200 WPM) fuer Hero, Cards und Single Posts

## Deployment als ZIP
```bash
zip -r ailinux-nova-dark.zip ailinux-nova-dark -x "*/node_modules/*" "*/.git/*"
```
Zip kann direkt im WordPress-Backend installiert werden.
