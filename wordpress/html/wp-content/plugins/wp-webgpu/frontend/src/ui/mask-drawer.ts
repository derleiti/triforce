export function createMaskUI(toolbar: HTMLElement, imageCanvas: HTMLCanvasElement, maskCanvas: HTMLCanvasElement) {
  // Malen erfolgt auf maskCanvas (Schwarz/Weiß)
  const ctx = maskCanvas.getContext('2d')!;
  ctx.fillStyle = 'black'; ctx.fillRect(0,0,maskCanvas.width, maskCanvas.height);

  let drawing = false;
  let brush = 24;
  const brushSizeInput = document.createElement('input');
  brushSizeInput.type = 'range';
  brushSizeInput.min = '4';
  brushSizeInput.max = '64';
  brushSizeInput.value = String(brush);
  brushSizeInput.oninput = () => brush = parseInt(brushSizeInput.value, 10);

  const exportBtn = document.createElement('button');
  exportBtn.textContent = 'Maske exportieren & Inpaint';

  maskCanvas.addEventListener('pointerdown', e => { drawing = true; draw(e); });
  maskCanvas.addEventListener('pointermove', e => { if (drawing) draw(e); });
  window.addEventListener('pointerup', () => drawing = false);

  function draw(e: PointerEvent) {
    const rect = maskCanvas.getBoundingClientRect();
    const x = (e.clientX - rect.left) * maskCanvas.width / rect.width;
    const y = (e.clientY - rect.top)  * maskCanvas.height / rect.height;
    ctx.fillStyle = 'white';
    ctx.beginPath(); ctx.arc(x,y,brush,0,Math.PI*2); ctx.fill();
  }

  exportBtn.onclick = async () => {
    if (!window.NOVA_AI_CFG || !window.NOVA_AI_CFG.apiBase || !window.NOVA_AI_CFG.nonce) {
      console.error('NOVA_AI_CFG ist nicht korrekt initialisiert.');
      alert('Fehler: Plugin-Konfiguration fehlt.');
      return;
    }

    const maskBlob = await new Promise<Blob | null>(res => maskCanvas.toBlob(b => res(b!), 'image/png'));
    const imageBlob = await new Promise<Blob | null>(res => imageCanvas.toBlob(b => res(b!), 'image/png'));

    if (!maskBlob || !imageBlob) {
      alert('Fehler beim Erstellen der Blobs.');
      return;
    }

    const formData = new FormData();
    formData.append('image', imageBlob, 'image.png');
    formData.append('mask', maskBlob, 'mask.png');
    formData.append('prompt', 'Ein schönes Bild mit Inpainting'); // Beispiel-Prompt
    formData.append('strength', '0.7'); // Beispiel-Strength

    try {
      const response = await fetch(`${window.NOVA_AI_CFG.apiBase}/sd3/mask-inpaint`, {
        method: 'POST',
        body: formData,
        headers: {
          'X-WP-Nonce': window.NOVA_AI_CFG.nonce,
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      console.log('Inpaint-Ergebnis:', result);
      alert(`Inpainting erfolgreich! Bild-URL: ${result.image_url}`);
      // Hier könnte man das neue Bild im imageCanvas anzeigen
    } catch (error) {
      console.error('Fehler beim Inpainting:', error);
      alert(`Fehler beim Inpainting: ${error instanceof Error ? error.message : String(error)}`);
    }
  };

  toolbar.append(brushSizeInput, exportBtn);
}