
export class Node {
    constructor(type) {
        this.type = type;
    }
}

export class Program extends Node {
    constructor(body) {
        super('Program');
        this.body = body; // Array of statements
    }
}

export class MaterialDeclaration extends Node {
    constructor(name, properties) {
        super('MaterialDeclaration');
        this.name = name;
        this.properties = properties;
    }
}

export class Property extends Node {
    constructor(name, value) {
        super('Property');
        this.name = name;
        this.value = value;
    }
}

export class CallExpression extends Node {
    constructor(callee, args) {
        super('CallExpression');
        this.callee = callee;
        this.args = args;
    }
}

export class Literal extends Node {
    constructor(value) {
        super('Literal');
        this.value = value;
    }
}
