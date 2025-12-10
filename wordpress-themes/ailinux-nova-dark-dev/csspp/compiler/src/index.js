import { Lexer } from './lexer.js';
import { Parser } from './parser.js';
import { Transpiler } from './transpiler.js';
import fs from 'fs';

export function compile(input) {
    const lexer = new Lexer(input);
    const tokens = lexer.tokenize();
    
    const parser = new Parser(tokens);
    const ast = parser.parse();

    const transpiler = new Transpiler();
    return transpiler.compile(ast);
}

// CLI Runner (if run directly)
if (process.argv[1].endsWith('index.js')) {
    const inputFile = process.argv[2];
    if (inputFile) {
        const input = fs.readFileSync(inputFile, 'utf-8');
        console.log(compile(input));
    }
}
