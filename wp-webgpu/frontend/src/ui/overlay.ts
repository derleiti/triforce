type BBox = { x:number; y:number; w:number; h:number; label:string; conf:number };

export function createOverlayUI(toolbar: HTMLElement, overlayCanvas: HTMLCanvasElement) {
  const ctx = overlayCanvas.getContext('2d')!;
  const btn = document.createElement('button'); btn.textContent = 'Overlay aktualisieren';
  btn.onclick = async () => {
    ctx.clearRect(0,0,overlayCanvas.width, overlayCanvas.height);

    if (!window.NOVA_AI_CFG || !window.NOVA_AI_CFG.apiBase || !window.NOVA_AI_CFG.nonce) {
      console.error('NOVA_AI_CFG ist nicht korrekt initialisiert.');
      alert('Fehler: Plugin-Konfiguration fehlt.');
      return;
    }

    // Hier müsste das Bild, für das das Overlay erstellt werden soll, an das Backend gesendet werden.
    // Für diese Demo nehmen wir an, das Backend hat bereits ein Bild oder kann es verarbeiten.
    // In einer echten Anwendung würde man hier z.B. die URL des angezeigten Bildes senden.
    const payload = { image_url: 'demo_image_url.jpg' }; // Beispiel-Payload

    try {
      const response = await fetch(`${window.NOVA_AI_CFG.apiBase}/vision/overlay-data`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-WP-Nonce': window.NOVA_AI_CFG.nonce,
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
      const data: BBox[] = result.boxes || [];

      ctx.lineWidth = 2;
      data.forEach(b => {
        ctx.strokeStyle = 'lime';
        ctx.strokeRect(b.x, b.y, b.w, b.h);
        ctx.fillStyle = 'rgba(0,0,0,0.6)';
        const text = `${b.label} ${(b.conf*100).toFixed(1)}%`;
        const textWidth = ctx.measureText(text).width;
        ctx.fillRect(b.x, b.y-18, textWidth + 8, 18); // +8 für Padding
        ctx.fillStyle = 'white';
        ctx.fillText(text, b.x+4, b.y-5);
      });
    } catch (error) {
      console.error('Fehler beim Abrufen des Overlays:', error);
      alert(`Fehler beim Abrufen des Overlays: ${error instanceof Error ? error.message : String(error)}`);
    }
  };
  toolbar.append(btn);
}