# CSS++ Language Specification (Draft 1.0)

## 1. Philosophy
CSS++ is a modular design language for UI, 2D, pseudo-3D, and immersive themes. It abstracts visual properties into four core pillars: **Geometry**, **Lighting**, **Volumetrics**, and **Theme**.

## 2. Core Modules

### 2.1 Geometry (`geometry.csspp`)
Defines the physical shape and layout structure.
- **Keywords**: `shape`, `edge`, `grid`, `layout`
- **Example**:
  ```csspp
  shape: pill(12);
  edge: chamfer(4);
  grid: golden-ratio;
  ```

### 2.2 Lighting (`lighting.csspp`)
Defines how light interacts with the object.
- **Keywords**: `light`, `shadow`, `reflection`, `surface`
- **Example**:
  ```csspp
  light: ambient(0.6);
  shadow: drop(2, 0.3);
  reflection: subtle(0.1);
  ```

### 2.3 Volumetrics (`volumetrics.csspp`)
Defines the material properties and depth.
- **Keywords**: `texture`, `density`, `depth`, `grain`
- **Example**:
  ```csspp
  texture: grain(0.2);
  density: airy;
  depth: layer(3);
  ```

### 2.4 Theme (`theme.csspp`)
Defines the aesthetic variables and tokens.
- **Keywords**: `color`, `spacing`, `radius`, `curve`
- **Example**:
  ```csspp
  color: var(--primary-500);
  spacing: 8;
  radius: 12;
  ```

## 3. Syntax

### 3.1 Material Declaration
The `@material` block is the primary unit of composition.

```csspp
@material card {
    geometry: rounded(12);
    lighting: soft(0.4);
    volumetrics: fabric(0.2);
    theme: primary;
}
```

### 3.2 Variables & Tokens
Standard CSS variables are supported, along with semantic aliases.

## 4. Compiler Pipeline
1. **Lexer**: Tokenizes the input stream.
2. **Parser**: Constructs an Abstract Syntax Tree (AST).
3. **Validator**: Checks for invalid modules or syntax errors.
4. **Transpiler**: Converts AST to valid CSS/SCSS.
