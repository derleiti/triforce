export const TokenType = {
    AT_KEYWORD: 'AT_KEYWORD',   // @material, @theme
    IDENTIFIER: 'IDENTIFIER',   // geometry, shape, pill
    NUMBER: 'NUMBER',           // 12, 0.5
    STRING: 'STRING',           // "value"
    LPAREN: 'LPAREN',           // (
    RPAREN: 'RPAREN',           // )
    LBRACE: 'LBRACE',           // {
    RBRACE: 'RBRACE',           // }
    COLON: 'COLON',             // :
    SEMICOLON: 'SEMICOLON',     // ;
    COMMA: 'COMMA',             // ,
    EOF: 'EOF'                  // End of file
};

export class Token {
    constructor(type, value, line, column) {
        this.type = type;
        this.value = value;
        this.line = line;
        this.column = column;
    }
}
