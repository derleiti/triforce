import { TokenType } from './tokens.js';
import { Program, MaterialDeclaration, Property, CallExpression, Literal } from './ast.js';

export class Parser {
    constructor(tokens) {
        this.tokens = tokens;
        this.pos = 0;
        this.currentToken = this.tokens[this.pos];
    }

    eat(type) {
        if (this.currentToken.type === type) {
            this.pos++;
            this.currentToken = this.tokens[this.pos];
        } else {
            throw new Error(`Unexpected token: expected ${type}, got ${this.currentToken.type} at line ${this.currentToken.line}`);
        }
    }

    parse() {
        const statements = [];
        while (this.currentToken.type !== TokenType.EOF) {
            statements.push(this.parseStatement());
        }
        return new Program(statements);
    }

    parseStatement() {
        if (this.currentToken.type === TokenType.AT_KEYWORD) {
            if (this.currentToken.value === 'material') {
                return this.parseMaterial();
            }
            throw new Error(`Unknown at-rule: @${this.currentToken.value}`);
        } else if (this.currentToken.type === TokenType.IDENTIFIER) {
            return this.parseProperty();
        }
        throw new Error(`Unexpected token in statement: ${this.currentToken.type}`);
    }

    parseMaterial() {
        this.eat(TokenType.AT_KEYWORD);
        const name = this.currentToken.value;
        this.eat(TokenType.IDENTIFIER);
        this.eat(TokenType.LBRACE);

        const properties = [];
        while (this.currentToken.type !== TokenType.RBRACE && this.currentToken.type !== TokenType.EOF) {
            properties.push(this.parseProperty());
        }

        this.eat(TokenType.RBRACE);
        return new MaterialDeclaration(name, properties);
    }

    parseProperty() {
        const name = this.currentToken.value;
        this.eat(TokenType.IDENTIFIER);
        this.eat(TokenType.COLON);
        
        const value = this.parseComplexValue();
        
        this.eat(TokenType.SEMICOLON);
        return new Property(name, value);
    }

    parseComplexValue() {
        // Check for single Function Call
        if (this.currentToken.type === TokenType.IDENTIFIER && this.tokens[this.pos + 1]?.type === TokenType.LPAREN) {
             return this.parseCallExpression(this.currentToken.value);
        }

        // Otherwise, consume tokens until semicolon
        let parts = [];
        while (this.currentToken.type !== TokenType.SEMICOLON && this.currentToken.type !== TokenType.EOF) {
            parts.push(this.currentToken.value);
            this.pos++;
            this.currentToken = this.tokens[this.pos];
        }
        
        let valueStr = parts.reduce((acc, curr, idx) => {
            const strCurr = String(curr);
            
            // Merge unit/symbol to previous token
            if (['px', '%', 'em', 'rem', 'vh', 'vw', 'deg', 'ms', 's', ','].includes(strCurr)) {
                return acc + strCurr;
            }
            
            // Merge negative sign from previous iteration? 
            // In this loop, `acc` is the string so far. 
            // If `acc` ends with `-`, no space.
            if (String(acc).endsWith('-')) return acc + strCurr;

            // If current is `-`, check if we should add space.
            // -12 is read as IDENTIFIER(-) NUMBER(12) or IDENTIFIER(-12)?
            // With my Lexer change, -12 is likely IDENTIFIER(-12) if it starts with -.
            
            return acc + (idx > 0 ? ' ' : '') + strCurr;
        }, '');

        return new Literal(valueStr);
    }

    parseCallExpression(name) {
        this.eat(TokenType.IDENTIFIER); 
        this.eat(TokenType.LPAREN);
        const args = [];
        
        if (this.currentToken.type !== TokenType.RPAREN) {
            args.push(this.parseArgument()); 
            while (this.currentToken.type === TokenType.COMMA) {
                this.eat(TokenType.COMMA);
                args.push(this.parseArgument());
            }
        }

        this.eat(TokenType.RPAREN);
        return new CallExpression(name, args);
    }

    parseArgument() {
        // Check for IDENTIFIER starting with '-' (negative number or var)
        if (this.currentToken.type === TokenType.IDENTIFIER && this.currentToken.value === '-') {
             this.eat(TokenType.IDENTIFIER);
             const nextVal = this.parseArgument(); // Recurse? No, expects literal
             // Assuming next is number
             if (nextVal.type === 'Literal') {
                 return new Literal('-' + nextVal.value);
             }
        }

        if (this.currentToken.type === TokenType.NUMBER) {
            const num = this.currentToken.value;
            this.eat(TokenType.NUMBER);
            
            if (this.currentToken.type === TokenType.IDENTIFIER) {
                 const unit = this.currentToken.value;
                 this.eat(TokenType.IDENTIFIER);
                 return new Literal(num + unit);
            }
            // Also check for %
            if (this.currentToken.type === TokenType.IDENTIFIER && this.currentToken.value === '%') {
                 this.eat(TokenType.IDENTIFIER);
                 return new Literal(num + '%');
            }
            
            return new Literal(num);
        }
        
        if (this.currentToken.type === TokenType.STRING) {
            const val = this.currentToken.value;
            this.eat(TokenType.STRING);
            return new Literal(val);
        }
        
        if (this.currentToken.type === TokenType.IDENTIFIER) {
             const val = this.currentToken.value;
             this.eat(TokenType.IDENTIFIER);
             return new Literal(val);
        }
        
        throw new Error(`Unexpected argument token: ${this.currentToken.type}`);
    }
}