export async function getDevice(): Promise<GPUDevice | null> {
  if (!("gpu" in navigator)) return null;
  try {
    const adapter = await (navigator as any).gpu.requestAdapter();
    if (!adapter) return null;
    const device = await adapter.requestDevice();
    return device ?? null;
  } catch {
    return null;
  }
}
