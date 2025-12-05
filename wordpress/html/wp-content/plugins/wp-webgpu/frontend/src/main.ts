import { getDevice } from "./webgpu/init";

async function bootstrap() {
  const device = await getDevice();
  if (!device) {
    // Fallback: CPU/Canvas2D/WebGL Pfad aktivieren
    console.warn("WebGPU not available – enabling fallback renderer");
    return;
  }
  // TODO: Pipeline/Shader laden und Renderloop starten
}

bootstrap().catch(console.error);