import { TokenType, Token } from './tokens.js';

export class Lexer {
    constructor(input) {
        this.input = input;
        this.pos = 0;
        this.line = 1;
        this.col = 1;
        this.currentChar = this.input.length > 0 ? this.input[0] : null;
    }

    advance() {
        if (this.currentChar === '\n') {
            this.line++;
            this.col = 0;
        }
        this.pos++;
        this.col++;
        this.currentChar = this.pos < this.input.length ? this.input[this.pos] : null;
    }

    peek() {
        const nextPos = this.pos + 1;
        return nextPos < this.input.length ? this.input[nextPos] : null;
    }

    skipWhitespace() {
        while (this.currentChar !== null && /\s/.test(this.currentChar)) {
            this.advance();
        }
    }

    readIdentifier() {
        let result = '';
        // Allow alphanumeric, dashes, underscores, and % for CSS units in identifiers (lazy approach)
        // Actually, strict separation is better, but for CSS passthrough:
        while (this.currentChar !== null && /[a-zA-Z0-9-_\.%]/.test(this.currentChar)) {
            result += this.currentChar;
            this.advance();
        }
        return result;
    }

    readNumber() {
        let result = '';
        let hasDot = false;
        while (this.currentChar !== null && (/[0-9]/.test(this.currentChar) || this.currentChar === '.')) {
            if (this.currentChar === '.') {
                if (hasDot) break; 
                hasDot = true;
            }
            result += this.currentChar;
            this.advance();
        }
        return parseFloat(result);
    }

    readString() {
        const quote = this.currentChar; 
        this.advance(); 
        let result = '';
        while (this.currentChar !== null && this.currentChar !== quote) {
            result += this.currentChar;
            this.advance();
        }
        this.advance(); 
        return result;
    }

    getNextToken() {
        while (this.currentChar !== null) {
            if (/\s/.test(this.currentChar)) {
                this.skipWhitespace();
                continue;
            }

            // Comments (// style)
            if (this.currentChar === '/' && this.peek() === '/') {
                while (this.currentChar !== null && this.currentChar !== '\n') {
                    this.advance();
                }
                continue;
            }

            // Block Comments (/* style */)
            if (this.currentChar === '/' && this.peek() === '*') {
                this.advance(); // eat /
                this.advance(); // eat *
                while (this.currentChar !== null) {
                    if (this.currentChar === '*' && this.peek() === '/') {
                        this.advance(); // eat *
                        this.advance(); // eat /
                        break;
                    }
                    this.advance();
                }
                continue;
            }

            if (this.currentChar === '@') {
                this.advance();
                const name = this.readIdentifier();
                return new Token(TokenType.AT_KEYWORD, name, this.line, this.col);
            }

            // Punctuation
            switch (this.currentChar) {
                case '{': this.advance(); return new Token(TokenType.LBRACE, '{', this.line, this.col);
                case '}': this.advance(); return new Token(TokenType.RBRACE, '}', this.line, this.col);
                case '(': this.advance(); return new Token(TokenType.LPAREN, '(', this.line, this.col);
                case ')': this.advance(); return new Token(TokenType.RPAREN, ')', this.line, this.col);
                case ':': this.advance(); return new Token(TokenType.COLON, ':', this.line, this.col);
                case ';': this.advance(); return new Token(TokenType.SEMICOLON, ';', this.line, this.col);
                case ',': this.advance(); return new Token(TokenType.COMMA, ',', this.line, this.col);
                case '"':
                case "'":
                    return new Token(TokenType.STRING, this.readString(), this.line, this.col);
            }

            // Numbers (Check before identifiers to catch 12)
            if (/[0-9]/.test(this.currentChar)) {
                return new Token(TokenType.NUMBER, this.readNumber(), this.line, this.col);
            }

            // Identifiers (Catch-all for keywords, properties, units like 80%, etc if mixed)
            // Note: If readIdentifier supports %, 80% might be split into NUMBER(80) PERCENT(%) by logic above
            // UNLESS we check for start char. 
            // My readNumber handles digits. 
            // If I have '80%', the '8' triggers readNumber. it consumes '80'. Returns. Next is '%'.
            // So '%' hits the switch. 
            // FIX: Add '%' to switch.
            if (this.currentChar === '%') {
                 this.advance();
                 return new Token(TokenType.IDENTIFIER, '%', this.line, this.col); 
                 // Returning as identifier lets it be joined in parser
            }

            if (/[a-zA-Z_-]/.test(this.currentChar)) {
                return new Token(TokenType.IDENTIFIER, this.readIdentifier(), this.line, this.col);
            }

            throw new Error(`Unexpected character: '${this.currentChar}' at line ${this.line}, col ${this.col}`);
        }

        return new Token(TokenType.EOF, null, this.line, this.col);
    }

    tokenize() {
        const tokens = [];
        let token;
        do {
            token = this.getNextToken();
            tokens.push(token);
        } while (token.type !== TokenType.EOF);
        return tokens;
    }
}