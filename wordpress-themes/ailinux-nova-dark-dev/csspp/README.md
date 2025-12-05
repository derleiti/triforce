# CSS++ Ecosystem

**Lead Architect:** Gemini (Zombie Context)
**Version:** 1.0.0 (Deep Dark Nova)

## 🏗 Project Structure

- **`spec/`**: The Source of Truth. Language specification.
- **`compiler/src/`**: The Node.js Compiler Pipeline.
  - `lexer.js`: Tokenizer.
  - `parser.js`: AST Builder.
  - `transpiler.js`: CSS Generator.
- **`examples/`**: Integration tests and demos.

## 🚀 Usage

Compile a `.csspp` file:

```bash
node csspp/compiler/src/index.js csspp/examples/demo.csspp
```

## 💎 Philosophy
CSS++ modularizes design into **Geometry**, **Lighting**, **Volumetrics**, and **Theme**.
