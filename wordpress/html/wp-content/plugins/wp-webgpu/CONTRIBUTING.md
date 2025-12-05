# Contributing to Nova AI WebGPU Frontend

Welcome! This guide explains how to contribute to the WebGPU-accelerated frontend component.

## Development Environment

### Prerequisites
- Node.js 18+ and npm
- TypeScript 5.5+
- Modern browser with WebGPU support
- WordPress development environment

### Setup
```bash
cd wp-webgpu/frontend
npm install
npm run dev        # Development server
npm run build      # Production build
npm run typecheck  # Type checking
```

## Architecture Overview

### Core Components
- **WebGPU Engine**: Hardware-accelerated processing
- **UI Layer**: User interface and controls
- **Shader System**: WGSL-based image processing
- **WordPress Integration**: Plugin compatibility

### Key Files
```
src/
├── webgpu/init.ts      # GPU device management
├── ui/overlay.ts       # Vision overlay interface
├── ui/mask-drawer.ts   # Interactive tools
├── compute/resize.wgsl # Image processing shaders
└── render/filters.wgsl # Visual effect shaders
```

## Development Guidelines

### TypeScript Standards
- Strict type checking enabled
- Use interfaces for complex objects
- Proper error handling with try/catch
- JSDoc comments for public APIs

### Shader Development
- Write WGSL shaders for GPU computations
- Optimize for parallel execution
- Include comments explaining algorithms
- Test across different GPU architectures

### Performance Considerations
- Minimize CPU-GPU data transfers
- Use appropriate workgroup sizes
- Profile shader performance
- Implement efficient memory management

## Testing

### Browser Compatibility
Test on:
- Chrome 113+ (primary target)
- Edge 113+ (full support)
- Safari 16.4+ (WebGL fallback)
- Firefox (WebGL fallback)

### Performance Testing
- Measure frame rates
- Monitor memory usage
- Test with various image sizes
- Validate fallback behavior

## Code Style

### Naming Conventions
```typescript
// Classes: PascalCase
class WebGPUManager { }

// Functions: camelCase
function initializeDevice() { }

// Constants: UPPER_SNAKE_CASE
const MAX_TEXTURE_SIZE = 4096;

// Interfaces: PascalCase with I prefix
interface IShaderConfig { }
```

### Error Handling
```typescript
try {
  const device = await getDevice();
  if (!device) {
    throw new Error('WebGPU not supported');
  }
  // Use device...
} catch (error) {
  console.error('GPU initialization failed:', error);
  // Fallback logic...
}
```

## Shader Development

### WGSL Best Practices
```wgsl
// Clear variable naming
@compute @workgroup_size(8, 8)
fn process_image(@builtin(global_invocation_id) id: vec3<u32>) {
    let pixel_coord = id.xy;

    // Early bounds checking
    if (pixel_coord.x >= texture_width || pixel_coord.y >= texture_height) {
        return;
    }

    // Process pixel...
}
```

### Optimization Tips
- Use shared memory for workgroup communication
- Minimize divergent branching
- Align data structures for GPU access patterns
- Profile and optimize bottlenecks

## Pull Request Process

1. **Branch**: Create from `main`
2. **Code**: Implement with tests
3. **Build**: Ensure `npm run build` succeeds
4. **Type Check**: Pass `npm run typecheck`
5. **Test**: Manual testing in supported browsers
6. **PR**: Submit with clear description

## Issue Reporting

### Template
```
**Environment:**
- Browser: Chrome 113
- OS: Windows 11
- WebGPU: Supported

**Steps to reproduce:**
1. Load the WebGPU interface
2. Attempt to process image
3. Observe error in console

**Expected behavior:**
Image processes successfully

**Actual behavior:**
Error: "GPU device lost"
```

## Security Considerations

- Validate all input data
- Sanitize file uploads
- Implement proper CORS handling
- Never expose sensitive GPU information

## Performance Monitoring

### Key Metrics
- Initialization time
- Frame processing time
- Memory usage
- Shader compilation time

### Profiling Tools
- Chrome DevTools Performance tab
- WebGPU error logging
- Memory usage monitoring
- Frame rate counters

## License

Contributions are licensed under GPL v2 or later, matching WordPress licensing requirements.