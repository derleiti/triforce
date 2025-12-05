# Nova AI WebGPU Frontend

A WebGPU-accelerated frontend for AI-powered image processing, vision overlays, and preprocessing. This component provides hardware-accelerated image manipulation using WebGPU technology for enhanced performance.

## Overview

The WebGPU frontend leverages modern browser GPU capabilities to provide:
- Real-time image processing and filtering
- Vision overlay rendering
- Mask drawing and editing
- Hardware-accelerated preprocessing

## Features

### 🚀 Hardware Acceleration
- WebGPU-powered image processing
- Real-time filter application
- GPU-accelerated vision overlays
- Optimized performance for modern GPUs

### 🎨 Image Processing
- Multiple filter effects (blur, sharpen, contrast, etc.)
- Real-time preview and adjustment
- Batch processing capabilities
- Non-destructive editing

### 👁️ Vision Overlays
- AI-generated overlay rendering
- Interactive mask editing
- Layer management
- Export capabilities

### ⚡ Performance
- GPU-accelerated computations
- Low latency processing
- Efficient memory management
- Fallback to CPU/WebGL when WebGPU unavailable

## Technical Architecture

### Core Components

#### WebGPU Engine (`src/webgpu/`)
- **init.ts**: WebGPU device initialization and management
- Hardware detection and capability checking
- Device memory management
- Shader compilation and pipeline setup

#### UI Components (`src/ui/`)
- **overlay.ts**: Vision overlay interface and controls
- **mask-drawer.ts**: Interactive mask drawing tools
- Real-time canvas manipulation
- User interaction handling

#### Compute Shaders (`src/compute/`)
- **resize.wgsl**: Image resizing and scaling operations
- GPU-accelerated resize algorithms
- Quality-preserving transformations

#### Render Shaders (`src/render/`)
- **filters.wgsl**: Real-time image filter effects
- Multiple filter implementations
- Performance-optimized shader code

### File Structure

```
wp-webgpu/
├── frontend/
│   ├── src/
│   │   ├── compute/
│   │   │   └── resize.wgsl          # Image resize shaders
│   │   ├── render/
│   │   │   └── filters.wgsl         # Filter effect shaders
│   │   ├── ui/
│   │   │   ├── mask-drawer.ts       # Mask drawing interface
│   │   │   └── overlay.ts           # Vision overlay controls
│   │   ├── webgpu/
│   │   │   └── init.ts              # WebGPU initialization
│   │   ├── index.css                # Main styles
│   │   └── main.ts                  # Application entry point
│   ├── package.json                 # Node.js dependencies
│   ├── tsconfig.json               # TypeScript configuration
│   └── vite.config.ts              # Vite build configuration
├── assets/
│   ├── main.css                    # Compiled styles
│   └── main.js                     # Compiled JavaScript
├── nova-ai-frontend.php            # WordPress integration
├── readme.txt                      # WordPress plugin info
└── README.md                       # This documentation
```

## Installation & Setup

### Prerequisites
- Node.js 18+ and npm
- Modern browser with WebGPU support (Chrome 113+, Edge 113+)
- WordPress environment for plugin integration

### Development Setup

1. **Install dependencies:**
   ```bash
   cd wp-webgpu/frontend
   npm install
   ```

2. **Start development server:**
   ```bash
   npm run dev
   ```

3. **Build for production:**
   ```bash
   npm run build
   ```

4. **Type checking:**
   ```bash
   npm run typecheck
   ```

### WordPress Integration

1. **Upload plugin files** to `wp-content/plugins/wp-webgpu/`
2. **Activate the plugin** through WordPress admin
3. **Use shortcode** in posts/pages: `[nova_ai_gpu]`

## API Integration

### Backend Communication

The frontend communicates with the Nova AI backend via REST API:

```typescript
// Configuration from WordPress
interface NovaAICfg {
  apiBase: string;
  nonce: string;
}

// API endpoints used
const endpoints = {
  overlayData: '/vision/overlay-data',
  // Additional endpoints as needed
};
```

### WordPress Configuration

Required WordPress configuration for proper functionality:

```php
// Plugin configuration
$nova_ai_cfg = array(
    'apiBase' => 'https://api.ailinux.me:9100',
    'nonce' => wp_create_nonce('nova_ai_gpu')
);

// Make config available to JavaScript
wp_localize_script('nova-ai-gpu', 'NOVA_AI_CFG', $nova_ai_cfg);
```

## WebGPU Implementation

### Device Initialization

```typescript
export async function getDevice(): Promise<GPUDevice | null> {
  // Check WebGPU support
  if (!("gpu" in navigator)) return null;

  try {
    // Request GPU adapter
    const adapter = await (navigator as any).gpu.requestAdapter();
    if (!adapter) return null;

    // Request GPU device
    const device = await adapter.requestDevice();
    return device ?? null;
  } catch {
    return null;
  }
}
```

### Shader Usage

#### Compute Shaders
Used for image processing operations that don't require rendering:

```wgsl
// Example resize shader
@compute @workgroup_size(8, 8)
fn resize(@builtin(global_invocation_id) id: vec3<u32>) {
    // Resize computation logic
}
```

#### Render Shaders
Used for visual effects and final rendering:

```wgsl
// Example filter shader
@fragment
fn filter(@location(0) uv: vec2<f32>) -> @location(0) vec4<f32> {
    // Filter effect logic
    return textureSample(texture, sampler, uv);
}
```

## Browser Support

### Full WebGPU Support
- **Chrome 113+** (Desktop & Android)
- **Edge 113+** (Desktop)
- **Opera 99+**

### Fallback Support
- **Safari 16.4+** (WebGL fallback)
- **Firefox** (WebGL fallback)
- **Older browsers** (Canvas2D fallback)

### Feature Detection

```typescript
const webgpuSupported = async (): Promise<boolean> => {
  if (!("gpu" in navigator)) return false;

  try {
    const adapter = await (navigator as any).gpu.requestAdapter();
    return adapter !== null;
  } catch {
    return false;
  }
};
```

## Performance Considerations

### Memory Management
- Efficient GPU buffer allocation
- Automatic cleanup of unused resources
- Texture memory optimization

### Shader Optimization
- Minimize shader switches
- Batch operations when possible
- Use appropriate workgroup sizes

### Fallback Strategies
- Automatic degradation to WebGL
- CPU-based processing for unsupported browsers
- Graceful error handling

## Development Guidelines

### Code Style
- **TypeScript**: Strict type checking enabled
- **ES2022**: Modern JavaScript features
- **WebGPU API**: Direct GPU programming

### Shader Development
- Use WGSL (WebGPU Shading Language)
- Optimize for parallel execution
- Minimize memory access patterns

### Testing
- Browser compatibility testing
- Performance benchmarking
- Memory leak detection

## Troubleshooting

### Common Issues

**WebGPU not available**
```
Error: WebGPU is not supported on this browser
```
- Update browser to latest version
- Check GPU drivers
- Enable WebGPU flags in Chrome

**Shader compilation failed**
```
Error: Shader compilation error
```
- Check WGSL syntax
- Verify shader compatibility
- Review browser console for details

**Memory allocation failed**
```
Error: Unable to allocate GPU memory
```
- Reduce image sizes
- Close other GPU-intensive applications
- Check available VRAM

### Debug Mode

Enable debug logging:

```typescript
const DEBUG = true;

if (DEBUG) {
  console.log('WebGPU device:', device);
  console.log('Adapter info:', adapter);
}
```

## Contributing

### Development Workflow
1. Create feature branch from `main`
2. Implement changes with TypeScript
3. Test across supported browsers
4. Run type checking: `npm run typecheck`
5. Build and test: `npm run build`
6. Submit pull request

### Code Standards
- Use TypeScript for all new code
- Follow WebGPU best practices
- Include JSDoc comments for public APIs
- Test performance impact of changes

## License

GPL v2 or later - same as WordPress.

## Changelog

### Version 0.1.0
- Initial WebGPU implementation
- Basic image processing shaders
- Vision overlay interface
- WordPress plugin integration
- Fallback rendering support

## Roadmap

### Planned Features
- [ ] Advanced filter effects
- [ ] Real-time video processing
- [ ] Multi-layer compositing
- [ ] Export to various formats
- [ ] Plugin API for custom shaders

### Performance Improvements
- [ ] Shader precompilation
- [ ] Memory pool management
- [ ] Parallel processing optimization
- [ ] Progressive loading