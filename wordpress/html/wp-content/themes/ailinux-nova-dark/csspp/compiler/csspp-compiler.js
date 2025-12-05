/**
 * CSS++ Compiler Prototype
 *
 * Transpiliert .csspp → Standard CSS + JSON-IR Assets
 *
 * @version 0.1.0-alpha
 */

class CSSPPCompiler {
  constructor(options = {}) {
    this.options = {
      outputDir: options.outputDir || './csspp-output',
      minify: options.minify || false,
      sourceMap: options.sourceMap || true,
      moduleDir: options.moduleDir || './csspp/modules',
      ...options
    };

    this.ast = null;
    this.errors = [];
    this.warnings = [];
    this.assets = {
      textures: {},
      audio: {},
      materials: {},
      geometries: {}
    };
  }

  /**
   * Haupteinstieg: Kompiliere CSS++ zu CSS + Assets
   */
  async compile(input, filename = 'input.csspp') {
    console.log(`[CSS++] Compiling ${filename}...`);

    try {
      // Phase 1: Preprocessing
      const preprocessed = await this.preprocess(input);

      // Phase 2: Lexing & Parsing
      this.ast = this.parse(preprocessed);

      // Phase 3: Semantic Analysis
      this.validate(this.ast);

      // Phase 4: Transformations
      const transformed = this.transform(this.ast);

      // Phase 5: Code Generation
      const css = this.generateCSS(transformed);
      const jsonIR = this.generateJSON(transformed);

      // Phase 6: Output
      return {
        css,
        json: jsonIR,
        assets: this.assets,
        errors: this.errors,
        warnings: this.warnings
      };
    } catch (error) {
      this.errors.push({ message: error.message, line: 0 });
      throw error;
    }
  }

  /**
   * Phase 1: Preprocessing
   * - Resolve @import statements
   * - Expand variables
   * - Process @theme, @material, @texture definitions
   */
  async preprocess(input) {
    let processed = input;

    // Import resolution
    const importRegex = /@import\s+["']([^"']+)["'];/g;
    const imports = [...input.matchAll(importRegex)];

    for (const match of imports) {
      const importPath = match[1];
      console.log(`[CSS++] Importing ${importPath}...`);
      // TODO: Load and inline imported files
      processed = processed.replace(match[0], `/* Imported: ${importPath} */`);
    }

    // Theme expansion
    processed = this.expandThemes(processed);

    return processed;
  }

  /**
   * Expand @theme definitions into CSS variables
   */
  expandThemes(input) {
    const themeRegex = /@theme\s+([\w-]+)\s*\{([^}]+)\}/g;
    let output = input;

    const themes = [...input.matchAll(themeRegex)];

    for (const match of themes) {
      const [fullMatch, themeName, themeBody] = match;
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
   * Parse theme properties into key-value pairs
   */
  parseThemeProperties(themeBody) {
    const properties = {};
    // Strip comments
    const cleanBody = themeBody.replace(/\/\*[\s\S]*?\*\//g, '');
    const lines = cleanBody.split(';').filter(l => l.trim());

    for (const line of lines) {
      const [key, value] = line.split(':').map(s => s.trim());
      if (key && value) {
        properties[key] = value;
      }
    }

    return properties;
  }

  /**
   * Phase 2: Parse CSS++ into AST
   * (Simplified - real implementation would use proper parser)
   */
  parse(input) {
    // Minimal AST structure
    const ast = {
      type: 'StyleSheet',
      rules: []
    };

    // Extract rules (selector + declarations)
    const ruleRegex = /([^{]+)\{([^}]+)\}/g;
    const rules = [...input.matchAll(ruleRegex)];

    for (const match of rules) {
      const [, selector, declarations] = match;

      const rule = {
        type: 'Rule',
        selector: selector.trim(),
        declarations: this.parseDeclarations(declarations)
      };

      ast.rules.push(rule);
    }

    return ast;
  }

  /**
   * Parse declarations into property-value pairs
   */
  parseDeclarations(declarationsStr) {
    const declarations = [];
    const lines = declarationsStr.split(';').filter(l => l.trim());

    for (const line of lines) {
      const [property, value] = line.split(':').map(s => s.trim());

      if (property && value) {
        declarations.push({
          type: 'Declaration',
          property: property,
          value: value,
          isCSSPP: this.isCSSPPProperty(property)
        });
      }
    }

    return declarations;
  }

  /**
   * Check if property is CSS++ specific
   */
  isCSSPPProperty(property) {
    const cssppProps = [
      'shape', 'pixel-grid', 'depth', 'curve',
      'light-intensity', 'shadow-type', 'reflectivity', 'glow-color',
      'fog-density', 'particle', 'bloom-strength', 'film-grain',
      'material', 'texture', 'roughness', 'metallic',
      'hover-sfx', 'click-sfx', 'cursor-move-sfx', 'ambient-sound'
    ];

    return cssppProps.some(prop => property.includes(prop));
  }

  /**
   * Phase 3: Semantic Validation
   */
  validate(ast) {
    for (const rule of ast.rules) {
      for (const decl of rule.declarations) {
        if (decl.isCSSPP) {
          this.validateProperty(decl, rule.selector);
        }
      }
    }

    if (this.errors.length > 0) {
      throw new Error(`Validation failed with ${this.errors.length} errors`);
    }
  }

  /**
   * Validate individual CSS++ property
   */
  validateProperty(declaration, selector) {
    const { property, value } = declaration;

    // Example validation rules
    if (property === 'depth' && !value.match(/(\d+(\.\d+)?rem|3d)/)) {
      this.errors.push({
        message: `Invalid depth value: ${value}`,
        selector,
        property
      });
    }

    if (property === 'light-intensity' && !value.match(/^(0?\.\d+|1\.0|ambient|directional)/)) {
      this.warnings.push({
        message: `Light intensity should be between 0.0 and 1.0`,
        selector,
        property
      });
    }
  }

  /**
   * Phase 4: Transform CSS++ properties to standard CSS
   */
  transform(ast) {
    const transformed = { ...ast };

    for (const rule of transformed.rules) {
      const newDeclarations = [];

      for (const decl of rule.declarations) {
        if (decl.isCSSPP) {
          // Transform CSS++ property to standard CSS
          const cssEquivalents = this.transformProperty(decl, rule.selector);
          newDeclarations.push(...cssEquivalents);
        } else {
          // Keep standard CSS as-is
          newDeclarations.push(decl);
        }
      }

      rule.declarations = newDeclarations;
    }

    return transformed;
  }

  /**
   * Transform single CSS++ property to CSS equivalent(s)
   */
  transformProperty(declaration, selector) {
    const { property, value } = declaration;
    const results = [];

    // Geometry transformations
    if (property === 'shape') {
      if (value === 'circle') {
        results.push({ property: 'border-radius', value: '50%' });
      } else if (value.startsWith('rounded-rect')) {
        const radius = value.match(/rounded-rect\(([^)]+)\)/)?.[1] || '0.5rem';
        results.push({ property: 'border-radius', value: radius });
      } else if (value.startsWith('polygon')) {
        const sides = value.match(/polygon\((\d+)\)/)?.[1] || 6;
        const path = this.generatePolygonPath(parseInt(sides));
        results.push({ property: 'clip-path', value: `polygon(${path})` });
      }
    }

    // Lighting transformations
    if (property === 'shadow-type') {
      const shadowMap = {
        'soft': '0 4px 12px rgba(0, 0, 0, 0.15)',
        'hard': '0 2px 4px rgba(0, 0, 0, 0.3)',
        'contact': '0 1px 2px rgba(0, 0, 0, 0.2)'
      };
      const shadow = shadowMap[value] || shadowMap['soft'];
      results.push({ property: 'box-shadow', value: shadow });
    }

    if (property === 'glow-color') {
      results.push({ property: 'box-shadow', value: `0 0 20px ${value}` });
      results.push({ property: 'filter', value: 'brightness(1.2)' });
    }

    // Texture transformations
    if (property === 'material' && value.includes('brushed-metal')) {
      results.push({
        property: 'background',
        value: 'linear-gradient(135deg, #e0e0e0 0%, #f0f0f0 50%, #e0e0e0 100%)'
      });
    }

    // Audio transformations (export to JSON)
    if (property.includes('-sfx') || property.includes('ambient-sound')) {
      this.assets.audio[selector] = this.assets.audio[selector] || {};
      this.assets.audio[selector][property] = value;
      // No CSS output for audio properties
      return [];
    }

    return results;
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
   * Phase 5: Generate standard CSS output
   */
  generateCSS(ast) {
    let css = '/* Generated by CSS++ Compiler v0.1.0 */\n\n';

    for (const rule of ast.rules) {
      css += `${rule.selector} {\n`;

      for (const decl of rule.declarations) {
        css += `  ${decl.property}: ${decl.value};\n`;
      }

      css += '}\n\n';
    }

    return css;
  }

  /**
   * Phase 6: Generate JSON Intermediate Representation
   */
  generateJSON(ast) {
    return {
      version: '0.1.0',
      timestamp: new Date().toISOString(),
      assets: this.assets,
      metadata: {
        rules: ast.rules.length,
        errors: this.errors.length,
        warnings: this.warnings.length
      }
    };
  }
}

// Export for Node.js or browser
if (typeof module !== 'undefined' && module.exports) {
  module.exports = CSSPPCompiler;
}

// CLI Usage Example
if (require.main === module) {
  const fs = require('fs');
  const path = require('path');

  const args = process.argv.slice(2);

  if (args.length === 0) {
    console.log('Usage: node csspp-compiler.js <input.csspp> [output-dir]');
    process.exit(1);
  }

  const inputFile = args[0];
  const outputDir = args[1] || './csspp-output';

  const input = fs.readFileSync(inputFile, 'utf-8');
  const compiler = new CSSPPCompiler({ outputDir });

  compiler.compile(input, inputFile).then(result => {
    // Write CSS
    const cssPath = path.join(outputDir, path.basename(inputFile, '.csspp') + '.css');
    fs.writeFileSync(cssPath, result.css);
    console.log(`[CSS++] CSS written to ${cssPath}`);

    // Write JSON IR
    const jsonPath = path.join(outputDir, path.basename(inputFile, '.csspp') + '.assets.json');
    fs.writeFileSync(jsonPath, JSON.stringify(result.json, null, 2));
    console.log(`[CSS++] Assets written to ${jsonPath}`);

    // Summary
    console.log(`[CSS++] Compilation complete!`);
    console.log(`  Errors: ${result.errors.length}`);
    console.log(`  Warnings: ${result.warnings.length}`);

    if (result.errors.length > 0) {
      console.error('\nErrors:');
      result.errors.forEach(err => console.error(`  - ${err.message}`));
    }

    if (result.warnings.length > 0) {
      console.warn('\nWarnings:');
      result.warnings.forEach(warn => console.warn(`  - ${warn.message}`));
    }
  }).catch(err => {
    console.error(`[CSS++] Compilation failed:`, err.message);
    process.exit(1);
  });
}
