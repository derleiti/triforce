// WebGPU support for enhanced AI visualizations
// Fallback to Canvas 2D if WebGPU not supported

class AilinuxWebGPU {
    constructor() {
        this.canvas = null;
        this.context = null;
        this.device = null;
        this.fallbackCanvas = null;
        this.fallbackCtx = null;
        this.isSupported = false;
        this.animationId = null;
    }

    async init() {
        if (!navigator.gpu) {
            console.warn('WebGPU not supported, falling back to Canvas 2D');
            this.initFallback();
            return;
        }

        try {
            const adapter = await navigator.gpu.requestAdapter();
            if (!adapter) throw new Error('No adapter found');
            this.device = await adapter.requestDevice();
            this.isSupported = true;
            this.initWebGPU();
        } catch (error) {
            console.error('WebGPU initialization failed:', error);
            this.initFallback();
        }
    }

    initWebGPU() {
        this.canvas = document.createElement('canvas');
        this.canvas.width = 400;
        this.canvas.height = 300;
        this.context = this.canvas.getContext('webgpu');
        
        // Create shader modules for particle simulation
        const shaderModule = this.device.createShaderModule({
            code: `
                @vertex fn vs_main(@builtin(vertex_index) vertexIndex : u32) -> @builtin(position) vec4<f32> {
                    var pos = array<vec2<f32>, 3>(
                        vec2<f32>(-0.5, -0.5),
                        vec2<f32>( 0.5, -0.5),
                        vec2<f32>( 0.0,  0.5)
                    );
                    return vec4<f32>(pos[vertexIndex], 0.0, 1.0);
                }

                @fragment fn fs_main() -> @location(0) vec4<f32> {
                    return vec4<f32>(0.0, 0.5, 1.0, 1.0); // Blue particles
                }
            `
        });

        // Create render pipeline
        const pipeline = this.device.createRenderPipeline({
            vertex: {
                module: shaderModule,
                entryPoint: 'vs_main'
            },
            fragment: {
                module: shaderModule,
                entryPoint: 'fs_main',
                targets: [{ format: 'bgra8unorm' }]
            },
            primitive: { topology: 'triangle-list' }
        });

        this.renderLoop(pipeline);
    }

    initFallback() {
        this.fallbackCanvas = document.createElement('canvas');
        this.fallbackCanvas.width = 400;
        this.fallbackCanvas.height = 300;
        this.fallbackCtx = this.fallbackCanvas.getContext('2d');
        this.animateFallback();
    }

    renderLoop(pipeline) {
        const render = () => {
            const commandEncoder = this.device.createCommandEncoder();
            const textureView = this.context.getCurrentTexture().createView();
            
            const renderPass = commandEncoder.beginRenderPass({
                colorAttachments: [{
                    view: textureView,
                    loadOp: 'clear',
                    storeOp: 'store',
                    clearValue: { r: 0.1, g: 0.1, b: 0.2, a: 1.0 }
                }]
            });

            renderPass.setPipeline(pipeline);
            renderPass.draw(3, 1, 0, 0);
            renderPass.end();

            this.device.queue.submit([commandEncoder.finish()]);
            this.animationId = requestAnimationFrame(render);
        };
        render();
    }

    animateFallback() {
        const animate = () => {
            this.fallbackCtx.fillStyle = 'rgba(10, 10, 20, 1)';
            this.fallbackCtx.fillRect(0, 0, 400, 300);
            
            // Draw animated particles
            for (let i = 0; i < 50; i++) {
                const x = Math.sin(Date.now() * 0.001 + i) * 100 + 200;
                const y = Math.cos(Date.now() * 0.001 + i) * 100 + 150;
                this.fallbackCtx.fillStyle = 'rgba(0, 128, 255, 0.8)';
                this.fallbackCtx.beginPath();
                this.fallbackCtx.arc(x, y, 3, 0, Math.PI * 2);
                this.fallbackCtx.fill();
            }
            
            this.animationId = requestAnimationFrame(animate);
        };
        animate();
    }

    getCanvas() {
        return this.isSupported ? this.canvas : this.fallbackCanvas;
    }

    destroy() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
        }
        if (this.device) {
            this.device.destroy();
        }
    }
}

// Export for use in AI panel
export { AilinuxWebGPU };