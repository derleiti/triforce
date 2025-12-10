import { Node } from './ast.js';

export class Transpiler {
    constructor() {
        this.indent = 0;
        this.extraRules = []; // Store side-effects like @keyframes or :hover rules
    }

    compile(node) {
        this.extraRules = []; // Reset
        let css = '';
        
        if (node.type === 'Program') {
            css = node.body.map(stmt => this.visit(stmt)).join('\n');
        } else {
            css = this.visit(node);
        }

        // Append extra rules (keyframes, hover states) at the bottom
        if (this.extraRules.length > 0) {
            css += '\n\n/* --- Runtime Generated Rules --- */\n';
            css += this.extraRules.join('\n');
        }
        
        return css;
    }

    visit(node) {
        switch (node.type) {
            case 'MaterialDeclaration': return this.visitMaterial(node);
            case 'Property': return this.visitProperty(node);
            case 'CallExpression': return this.visitCall(node);
            case 'Literal': return this.visitLiteral(node);
            default: throw new Error(`Unknown node type: ${node.type}`);
        }
    }

    visitMaterial(node) {
        // 1. Find selector property if exists
        let customSelector = null;
        const visibleProperties = [];
        
        for (const p of node.properties) {
            if (p.name === 'selector') {
                 if (p.value.type === 'Literal') {
                     // strip quotes if present
                     customSelector = p.value.value.replace(/^['"]|['"]$/g, ''); 
                 }
            } else {
                visibleProperties.push(p);
            }
        }

        // 2. Determine Selector
        this.currentSelector = customSelector ? customSelector : `.material-${node.name}`;

        // 3. Generate Body
        const body = visibleProperties.map(p => this.visit(p)).filter(Boolean).join('\n    ');
        return `${this.currentSelector} {\n    ${body}\n}`;
    }

    visitProperty(node) {
        const name = node.name;
        const value = node.value;

        if (name === 'geometry') return this.transformGeometry(value);
        if (name === 'lighting') return this.transformLighting(value);
        if (name === 'volumetrics') return this.transformVolumetrics(value);
        if (name === 'theme') return this.transformTheme(value);
        if (name === 'animation') return this.transformAnimation(value);
        if (name === 'layout') return this.transformLayout(value);

        const valStr = this.resolveValue(value);
        return `${name}: ${valStr};`;
    }

    resolveValue(node) {
        if (node.type === 'Literal') return node.value;
        if (node.type === 'CallExpression') return this.visitCall(node);
        return '';
    }

    visitLiteral(node) { return node.value; }

    visitCall(node) {
        const args = node.args.map(a => this.resolveValue(a)).join(', ');
        return `${node.callee}(${args})`;
    }

    // --- Transformers ---

    transformGeometry(valueNode) {
        if (valueNode.type === 'CallExpression') {
            const arg = valueNode.args[0]?.value;
            if (valueNode.callee === 'rounded') return `border-radius: ${arg}px; overflow: hidden;`;
            if (valueNode.callee === 'pill') return `border-radius: 9999px;`;
            if (valueNode.callee === 'circle') return `border-radius: 50%; aspect-ratio: 1 / 1;`;
        }
        return `/* Unknown geometry */`;
    }

    transformLighting(valueNode) {
        if (valueNode.type === 'CallExpression') {
            const arg = valueNode.args[0]?.value;
            
            if (valueNode.callee === 'soft') {
                return `box-shadow: 0 4px 20px rgba(0,0,0, ${arg}); transition: box-shadow 0.3s ease;`;
            }
            if (valueNode.callee === 'hard') {
                return `box-shadow: ${4 * arg}px ${4 * arg}px 0px rgba(0,0,0, 1); border: 1px solid #000;`;
            }
            if (valueNode.callee === 'hover-glow') {
                // Advanced: Generate a sibling :hover rule
                const intensity = parseFloat(arg) || 0.2;
                // Create a specific hover rule for the current selector
                const hoverRule = `${this.currentSelector}:hover { 
    box-shadow: 0 0 ${intensity * 60}px ${intensity * 10}px var(--theme-glow, rgba(255,255,255,0.2)); 
    transform: translateY(-1px);
}`;
                this.extraRules.push(hoverRule);
                return `transition: all 0.3s ease; box-shadow: 0 2px 10px rgba(0,0,0,0.1);`;
            }
            if (valueNode.callee === 'ambient') {
                return `--lighting-ambient: ${arg}; /* CSS++ Ambient Light */`;
            }
            if (valueNode.callee === 'glow') {
                return `filter: drop-shadow(0 0 ${arg * 10}px var(--theme-glow, rgba(255,255,255,0.5)));`;
            }
        }
        return `/* Unknown lighting */`;
    }

    transformVolumetrics(valueNode) {
        if (valueNode.type === 'CallExpression') {
            if (valueNode.callee === 'fabric') {
                const opacity = valueNode.args[0].value;
                return `background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='${opacity}'/%3E%3C/svg%3E");`;
            }
            if (valueNode.callee === 'glass') {
                const blur = valueNode.args[0].value;
                return `backdrop-filter: blur(${blur}px); -webkit-backdrop-filter: blur(${blur}px); background: rgba(20, 20, 30, 0.6); border: 1px solid rgba(255,255,255,0.1);`;
            }
            if (valueNode.callee === 'metallic') {
                 const opacity = valueNode.args[0].value;
                 return `background: linear-gradient(135deg, rgba(255,255,255,${opacity * 0.1}) 0%, rgba(0,0,0,${opacity * 0.1}) 100%); box-shadow: inset 0 1px 0 rgba(255,255,255,0.2);`;
            }
        }
        return `/* Unknown volumetrics */`;
    }

    transformTheme(valueNode) {
        const val = this.resolveValue(valueNode);
        // Auto-generate readable/contrast text color var
        return `background-color: var(--theme-${val}, var(--${val}, #1a1a1a)); color: var(--text-on-${val}, var(--text-main, #fff)); --theme-glow: var(--${val});`;
    }

    transformAnimation(valueNode) {
        if (valueNode.type === 'CallExpression') {
            const duration = valueNode.args[0]?.value || '300ms';
            
            if (valueNode.callee === 'fade-in') {
                this.addKeyframe('csspp-fade-in', 'from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); }');
                return `animation: csspp-fade-in ${duration} ease-out forwards;`;
            }
            if (valueNode.callee === 'slide-up') {
                 this.addKeyframe('csspp-slide-up', 'from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); }');
                 return `animation: csspp-slide-up ${duration} cubic-bezier(0.2, 0.8, 0.2, 1) forwards;`;
            }
            if (valueNode.callee === 'pulse') {
                this.addKeyframe('csspp-pulse', '0% { transform: scale(1); } 50% { transform: scale(1.05); } 100% { transform: scale(1); }');
                return `animation: csspp-pulse ${duration} infinite ease-in-out;`;
            }
        }
        return `animation: ${this.resolveValue(valueNode)};`;
    }

    transformLayout(valueNode) {
        if (valueNode.type === 'CallExpression') {
            const gap = valueNode.args[0]?.value || 0;
            if (valueNode.callee === 'stack') return `display: flex; flex-direction: column; gap: ${gap}px;`;
            if (valueNode.callee === 'row') return `display: flex; flex-direction: row; align-items: center; gap: ${gap}px;`;
            if (valueNode.callee === 'grid') return `display: grid; grid-template-columns: repeat(auto-fit, minmax(${gap}px, 1fr)); gap: 1rem;`;
        }
        return `display: block;`;
    }

    addKeyframe(name, content) {
        const rule = `@keyframes ${name} { ${content} }`;
        if (!this.extraRules.includes(rule)) {
            this.extraRules.push(rule);
        }
    }
}
