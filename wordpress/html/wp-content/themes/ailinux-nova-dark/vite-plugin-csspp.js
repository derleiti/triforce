/**
 * Vite Plugin: CSS++ Compiler Integration
 *
 * Kompiliert .csspp-Dateien zu CSS während des Vite-Builds
 *
 * @version 1.0.0
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * CSS++ Compiler (Simplified for Vite Integration)
 */
class CSSPPCompilerSimple {
  constructor() {
    this.assets = {
      audio: {},
      textures: {},
      materials: {}
    };
  }

  /**
   * Compile CSS++ to CSS
   */
  compile(input, filename) {
    console.log(`[CSS++] Compiling ${filename}...`);

    // Phase 1: Expand @theme directives
    let output = this.expandThemes(input);

    // Phase 2: Transform CSS++ properties
    output = this.transformProperties(output);

    // Phase 3: Remove CSS++ comments
    output = this.removeComments(output);

    return {
      css: output,
      assets: this.assets
    };
  }

  /**
   * Expand @theme definitions
   */
  expandThemes(input) {
    const themeRegex = /@theme\s+(\w+)\s*\{([^}]+)\}/g;
    let output = input;

    const themes = [...input.matchAll(themeRegex)];

    for (const [fullMatch, themeName, themeBody] of themes) {
      const variables = this.parseThemeProperties(themeBody);

      // Generate CSS custom properties
      let cssVars = `:root[data-theme="${themeName}"] {\n`;
      for (const [key, value] of Object.entries(variables)) {
        cssVars += `  --theme-${key}: ${value};\n`;
      }
      cssVars += `}\n`;

      output = output.replace(fullMatch, cssVars);
    }

    return output;
  }

  /**
   * Parse theme properties
   */
  parseThemeProperties(themeBody) {
    const properties = {};
    const lines = themeBody.split(';').filter(l => l.trim());

    for (const line of lines) {
      const [key, value] = line.split(':').map(s => s.trim());
      if (key && value) {
        properties[key] = value;
      }
    }

    return properties;
  }

  /**
   * Transform CSS++ properties to standard CSS
   */
  transformProperties(input) {
    let output = input;

    // Transform shape: circle → border-radius: 50%
    output = output.replace(/shape:\s*circle/g, 'border-radius: 50%');

    // Transform shape: rounded-rect(...) → border-radius: ...
    output = output.replace(/shape:\s*rounded-rect\(([^)]+)\)/g, 'border-radius: $1');

    // Transform shape: polygon(n) → clip-path: polygon(...)
    output = output.replace(/shape:\s*polygon\((\d+)\)/g, (match, sides) => {
      return `clip-path: polygon(${this.generatePolygonPath(parseInt(sides))})`;
    });

    // Transform shadow-type: soft/hard/contact
    output = output.replace(/shadow-type:\s*(soft|hard|contact)/g, (match, type) => {
      const shadows = {
        soft: '0 4px 12px rgba(0, 0, 0, 0.15)',
        hard: '0 2px 4px rgba(0, 0, 0, 0.3)',
        contact: '0 1px 2px rgba(0, 0, 0, 0.2)'
      };
      return `box-shadow: ${shadows[type]}`;
    });

    // Transform glow-color → box-shadow + filter
    output = output.replace(/glow-color:\s*([^;]+);/g, (match, color) => {
      return `box-shadow: 0 0 20px ${color};\n  filter: brightness(1.2);`;
    });

    // Transform depth: <value> → box-shadow
    output = output.replace(/depth:\s*([\d.]+rem)/g, (match, value) => {
      const depth = parseFloat(value);
      return `box-shadow: 0 ${depth} ${depth * 2} rgba(0, 0, 0, 0.15)`;
    });

    // Transform depth: 3d → transform-style: preserve-3d
    output = output.replace(/depth:\s*3d/g, 'transform-style: preserve-3d');

    // Transform material: brushed-metal → background gradient
    output = output.replace(/material:\s*brushed-metal[^;]*;/g,
      'background: linear-gradient(135deg, #e0e0e0 0%, #f0f0f0 50%, #e0e0e0 100%);');

    // Extract and remove audio properties
    output = this.extractAudioProperties(output);

    return output;
  }

  /**
   * Generate polygon clip-path points
   */
  generatePolygonPath(sides) {
    const points = [];
    for (let i = 0; i < sides; i++) {
      const angle = (i * 2 * Math.PI) / sides - Math.PI / 2;
      const x = 50 + 50 * Math.cos(angle);
      const y = 50 + 50 * Math.sin(angle);
      points.push(`${x.toFixed(2)}% ${y.toFixed(2)}%`);
    }
    return points.join(', ');
  }

  /**
   * Extract audio properties and store in assets
   */
  extractAudioProperties(input) {
    const audioRegex = /(\.[\w-]+)\s*\{([^}]*(?:hover-sfx|click-sfx|cursor-move-sfx|ambient-sound)[^}]*)\}/g;
    let output = input;

    const matches = [...input.matchAll(audioRegex)];

    for (const [fullMatch, selector, ruleBody] of matches) {
      const hoverMatch = ruleBody.match(/hover-sfx:\s*([^;]+);/);
      const clickMatch = ruleBody.match(/click-sfx:\s*([^;]+);/);
      const cursorMatch = ruleBody.match(/cursor-move-sfx:\s*([^;]+);/);
      const ambientMatch = ruleBody.match(/ambient-sound:\s*([^;]+);/);

      if (hoverMatch || clickMatch || cursorMatch || ambientMatch) {
        this.assets.audio[selector] = {};

        if (hoverMatch) this.assets.audio[selector]['hover-sfx'] = hoverMatch[1].trim();
        if (clickMatch) this.assets.audio[selector]['click-sfx'] = clickMatch[1].trim();
        if (cursorMatch) this.assets.audio[selector]['cursor-move-sfx'] = cursorMatch[1].trim();
        if (ambientMatch) this.assets.audio[selector]['ambient-sound'] = ambientMatch[1].trim();

        // Remove audio properties from CSS
        output = output.replace(/hover-sfx:\s*[^;]+;/g, '');
        output = output.replace(/click-sfx:\s*[^;]+;/g, '');
        output = output.replace(/cursor-move-sfx:\s*[^;]+;/g, '');
        output = output.replace(/ambient-sound:\s*[^;]+;/g, '');
      }
    }

    return output;
  }

  /**
   * Remove CSS++ specific comments
   */
  removeComments(input) {
    // Keep standard CSS comments, remove CSS++ metadata
    return input;
  }
}

/**
 * Vite Plugin Factory
 */
export default function cssppPlugin(options = {}) {
  const {
    include = /\.csspp$/,
    outputDir = 'csspp-output',
    generateAssets = true
  } = options;

  const compiler = new CSSPPCompilerSimple();
  const compiledFiles = new Map();

  return {
    name: 'vite-plugin-csspp',

    /**
     * Transform .csspp files to CSS
     */
    transform(code, id) {
      if (!include.test(id)) {
        return null;
      }

      console.log(`[vite-plugin-csspp] Transforming ${path.basename(id)}`);

      try {
        const result = compiler.compile(code, id);
        const css = result.css;

        // Store compiled result
        compiledFiles.set(id, result);

        // Return as CSS module
        return {
          code: `export default ${JSON.stringify(css)}`,
          map: null
        };
      } catch (error) {
        console.error(`[vite-plugin-csspp] Error compiling ${id}:`, error);
        throw error;
      }
    },

    /**
     * Generate assets JSON after build
     */
    writeBundle(options, bundle) {
      if (!generateAssets || compiledFiles.size === 0) {
        return;
      }

      // Merge all assets
      const mergedAssets = {
        version: '1.0.0',
        timestamp: new Date().toISOString(),
        assets: {
          audio: {},
          textures: {},
          materials: {}
        }
      };

      for (const [id, result] of compiledFiles.entries()) {
        Object.assign(mergedAssets.assets.audio, result.assets.audio);
        Object.assign(mergedAssets.assets.textures, result.assets.textures);
        Object.assign(mergedAssets.assets.materials, result.assets.materials);
      }

      // Write assets JSON
      const assetsJsonPath = path.join(options.dir, 'csspp-assets.json');
      fs.writeFileSync(assetsJsonPath, JSON.stringify(mergedAssets, null, 2));

      console.log(`[vite-plugin-csspp] Assets written to ${assetsJsonPath}`);
      console.log(`[vite-plugin-csspp] Audio bindings: ${Object.keys(mergedAssets.assets.audio).length}`);
    },

    /**
     * Dev server: Watch .csspp files
     */
    handleHotUpdate({ file, server }) {
      if (include.test(file)) {
        console.log(`[vite-plugin-csspp] Hot reload: ${path.basename(file)}`);
        // Trigger full reload for CSS++ changes
        server.ws.send({
          type: 'full-reload',
          path: '*'
        });
      }
    }
  };
}
