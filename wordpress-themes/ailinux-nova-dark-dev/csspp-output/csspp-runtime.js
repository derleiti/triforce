/**
 * CSS++ Audio Runtime (Prototype)
 *
 * Lädt Audio-Bindings aus .assets.json und spielt Sounds ab
 *
 * @version 0.1.0-alpha
 */

class CSSPPRuntime {
  constructor(assetsPath) {
    this.assetsPath = assetsPath;
    this.assets = null;
    this.audioContext = null;
    this.sounds = {};
    this.enabled = true;

    this.init();
  }

  async init() {
    try {
      // Lade Assets
      const response = await fetch(this.assetsPath);
      this.assets = await response.json();

      console.log('[CSS++ Runtime] Assets geladen:', this.assets);

      // Web Audio API Context
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)();

      // Binde Audio-Events an DOM-Elemente
      this.bindAudioEvents();

      console.log('[CSS++ Runtime] Initialisiert ✓');
    } catch (error) {
      console.warn('[CSS++ Runtime] Initialisierung fehlgeschlagen:', error);
      this.enabled = false;
    }
  }

  bindAudioEvents() {
    if (!this.assets || !this.assets.assets.audio) return;

    const audioBindings = this.assets.assets.audio;

    for (const [selector, sounds] of Object.entries(audioBindings)) {
      // Bereinige Selector (entferne Kommentare/Whitespace)
      const cleanSelector = this.cleanSelector(selector);

      if (!cleanSelector) continue;

      const elements = document.querySelectorAll(cleanSelector);

      elements.forEach(element => {
        // Hover-Sound
        if (sounds['hover-sfx']) {
          element.addEventListener('mouseenter', () => {
            this.playSound(sounds['hover-sfx']);
          });
        }

        // Click-Sound
        if (sounds['click-sfx']) {
          element.addEventListener('click', () => {
            this.playSound(sounds['click-sfx']);
          });
        }

        // Cursor-Move-Sound (throttled)
        if (sounds['cursor-move-sfx']) {
          let lastPlay = 0;
          element.addEventListener('mousemove', () => {
            const now = Date.now();
            if (now - lastPlay > 100) { // Throttle auf 100ms
              this.playSound(sounds['cursor-move-sfx']);
              lastPlay = now;
            }
          });
        }
      });

      console.log(`[CSS++ Runtime] Audio gebunden: ${cleanSelector}`, sounds);
    }
  }

  cleanSelector(selector) {
    // Extrahiere CSS-Selector aus dem JSON-Key (entferne Kommentare, Whitespace)
    const match = selector.match(/\.[\w-]+/);
    return match ? match[0] : null;
  }

  playSound(soundDefinition) {
    if (!this.enabled || !this.audioContext) return;

    console.log(`[CSS++ Runtime] 🔊 Play: ${soundDefinition}`);

    // Parse Sound-Definition
    const parsed = this.parseSoundDefinition(soundDefinition);

    if (!parsed) return;

    // Synthesize Sound
    this.synthesizeSound(parsed);
  }

  parseSoundDefinition(definition) {
    // Einfaches Parsing für Demo
    // chime(440Hz) → { type: 'chime', frequency: 440 }
    // click(mechanical) → { type: 'click', style: 'mechanical' }

    const chimeMatch = definition.match(/chime\((\d+)Hz/);
    if (chimeMatch) {
      return {
        type: 'chime',
        frequency: parseInt(chimeMatch[1]),
        decay: 0.3
      };
    }

    const clickMatch = definition.match(/click\((\w+)\)/);
    if (clickMatch) {
      return {
        type: 'click',
        style: clickMatch[1]
      };
    }

    const popMatch = definition.match(/pop\(([\d.]+)\)/);
    if (popMatch) {
      return {
        type: 'pop',
        intensity: parseFloat(popMatch[1])
      };
    }

    return null;
  }

  synthesizeSound(sound) {
    const now = this.audioContext.currentTime;

    if (sound.type === 'chime') {
      // Synthesize Chime
      const oscillator = this.audioContext.createOscillator();
      const gainNode = this.audioContext.createGain();

      oscillator.type = 'sine';
      oscillator.frequency.setValueAtTime(sound.frequency, now);

      gainNode.gain.setValueAtTime(0.3, now);
      gainNode.gain.exponentialRampToValueAtTime(0.01, now + sound.decay);

      oscillator.connect(gainNode);
      gainNode.connect(this.audioContext.destination);

      oscillator.start(now);
      oscillator.stop(now + sound.decay);

    } else if (sound.type === 'click') {
      // Synthesize Click (kurzer Noise-Burst)
      const bufferSize = 4096;
      const buffer = this.audioContext.createBuffer(1, bufferSize, this.audioContext.sampleRate);
      const data = buffer.getChannelData(0);

      for (let i = 0; i < bufferSize; i++) {
        data[i] = Math.random() * 2 - 1;
      }

      const source = this.audioContext.createBufferSource();
      source.buffer = buffer;

      const gainNode = this.audioContext.createGain();
      gainNode.gain.setValueAtTime(0.1, now);
      gainNode.gain.exponentialRampToValueAtTime(0.01, now + 0.05);

      source.connect(gainNode);
      gainNode.connect(this.audioContext.destination);

      source.start(now);

    } else if (sound.type === 'pop') {
      // Synthesize Pop (kurzer Bass-Hit)
      const oscillator = this.audioContext.createOscillator();
      const gainNode = this.audioContext.createGain();

      oscillator.type = 'sine';
      oscillator.frequency.setValueAtTime(100, now);
      oscillator.frequency.exponentialRampToValueAtTime(50, now + 0.1);

      gainNode.gain.setValueAtTime(sound.intensity * 0.5, now);
      gainNode.gain.exponentialRampToValueAtTime(0.01, now + 0.15);

      oscillator.connect(gainNode);
      gainNode.connect(this.audioContext.destination);

      oscillator.start(now);
      oscillator.stop(now + 0.15);
    }
  }

  enable() {
    this.enabled = true;
    console.log('[CSS++ Runtime] Audio aktiviert');
  }

  disable() {
    this.enabled = false;
    console.log('[CSS++ Runtime] Audio deaktiviert');
  }

  toggle() {
    this.enabled = !this.enabled;
    console.log(`[CSS++ Runtime] Audio ${this.enabled ? 'aktiviert' : 'deaktiviert'}`);
  }
}

// Auto-Init wenn DOM bereit
if (typeof document !== 'undefined') {
  document.addEventListener('DOMContentLoaded', () => {
    // Suche nach .assets.json im selben Verzeichnis
    const currentScript = document.currentScript;
    if (currentScript) {
      const scriptDir = currentScript.src.substring(0, currentScript.src.lastIndexOf('/'));
      const assetsPath = scriptDir + '/demo-simple.assets.json';

      window.cssppRuntime = new CSSPPRuntime(assetsPath);
    }
  });
}

// Export für Module
if (typeof module !== 'undefined' && module.exports) {
  module.exports = CSSPPRuntime;
}
