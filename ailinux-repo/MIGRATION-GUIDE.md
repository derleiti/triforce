# Migration Guide: Erweiterte multiverse + i386 Konfiguration

## Übersicht der Änderungen

### ✅ Was bereits funktioniert (alte mirror.list)
- Ubuntu Base Repositories mit multiverse für amd64+i386
- KDE Neon, Xubuntu, Docker, Chrome, WineHQ
- Insgesamt ~630-700 GB Mirror

### 🚀 Neue Funktionen (mirror.list.new)

#### Hinzugefügte Repositories mit i386-Unterstützung:

**Developer Tools:**
- Git Stable PPA (git-core/ppa) - amd64+i386
- NodeJS 20.x (nodesource) - amd64+i386
- Python (deadsnakes/ppa) - amd64+i386

**Gaming (KRITISCH für i386):**
- Lutris PPA (lutris-team/lutris) - amd64+i386
- Graphics Drivers PPA (graphics-drivers/ppa) - amd64+i386
  - NVIDIA/AMD-Treiber mit 32-bit Unterstützung
  - Wichtig für Steam und Gaming

**Multimedia:**
- OBS Studio PPA (obsproject/obs-studio) - amd64+i386
- Kdenlive PPA (kdenlive/kdenlive-stable) - amd64+i386
- FFmpeg 4 & 5 PPAs (savoury1) - amd64+i386

**System Utilities:**
- Timeshift Backup (teejee2008/timeshift) - amd64+i386
- BleachBit Cleaner (n-muench/programs-ppa) - amd64+i386

**Browser:**
- Brave Browser - amd64+i386

**Source Packages:**
- Ubuntu deb-src für main, restricted, universe, multiverse
- Optional: kann auskommentiert werden um ~100 GB zu sparen

## Warum ist i386-Unterstützung wichtig?

### Gaming:
- **Steam**: Benötigt ZWINGEND i386-Bibliotheken (32-bit Runtime)
- **Wine/Proton**: Viele Windows-Games laufen mit 32-bit
- **Graphics Drivers**: NVIDIA/AMD-Treiber brauchen 32-bit Libs für alte Games

### Legacy Software:
- Ältere proprietäre Software (z.B. ältere Adobe-Tools unter Wine)
- 32-bit-only Anwendungen

### Multimedia:
- Einige alte Codecs und Filter sind nur als 32-bit verfügbar
- Compatibility-Layer für ältere Audio/Video-Software

## Migration Steps

### 1. Backup erstellen (als root/sudo)
```bash
sudo cp /home/zombie/ailinux-repo/repo/mirror/mirror.list \
        /home/zombie/ailinux-repo/repo/mirror/mirror.list.backup-$(date +%Y%m%d)
```

### 2. Neue Konfiguration installieren
```bash
sudo cp /home/zombie/ailinux-repo/mirror.list.new \
        /home/zombie/ailinux-repo/repo/mirror/mirror.list
```

### 3. Mirror Update ausführen
```bash
cd /home/zombie/ailinux-repo
./update-mirror.sh
```

**WICHTIG:** Der erste Sync dauert DEUTLICH länger:
- Alte Konfiguration: ~630-700 GB, 4-8 Stunden
- Neue Konfiguration: ~800-900 GB, 6-12 Stunden
- Viele neue Repositories müssen komplett geladen werden

### 4. Post-Migration Validierung
```bash
# Self-Healing ausführen
./nova-heal.sh

# Repository-Signatur prüfen
./repo-health.sh

# Vollständige Health-Checks
./health.sh

# Troubleshooting bei Problemen
./troubleshoot.sh
```

## Disk Space Requirements

| Konfiguration | Geschätzte Größe | Delta zum Original |
|---------------|------------------|-------------------|
| Original mirror.list | 630-700 GB | - |
| Neue mirror.list (ohne deb-src) | 750-850 GB | +120-150 GB |
| Neue mirror.list (mit deb-src) | 850-950 GB | +220-250 GB |

## Selektive Migration (Optional)

Falls du nicht alle Repositories brauchst, kannst du die `mirror.list.new` editieren:

### Disk Space sparen:

**Source-Pakete entfernen (-100 GB):**
Kommentiere alle `deb-src` Zeilen aus (Zeile 20-23)

**Multimedia weglassen (-30 GB):**
Kommentiere FFmpeg, OBS, Kdenlive aus

**Gaming-Repos weglassen (-20 GB):**
Kommentiere Lutris und Graphics Drivers aus

### Empfohlene Minimal-Konfiguration:

Behalte auf jeden Fall:
- Ubuntu Base (main, restricted, universe, multiverse) - amd64+i386
- WineHQ - amd64+i386
- Graphics Drivers PPA - amd64+i386 (für Steam/Gaming)

## Client-Side Setup

Nach der Migration müssen Clients die neuen Repositories nutzen können:

### Auto-Setup (empfohlen):
```bash
curl -fsSL https://repo.ailinux.me:8443/mirror/setup-ailinux-mirror.sh | sudo bash
```

### Manuelle Setup:
```bash
# GPG Key installieren
curl -fsSL "https://repo.ailinux.me:8443/mirror/ailinux-archive-key.gpg" \
  | sudo tee /usr/share/keyrings/ailinux-archive-keyring.gpg >/dev/null

# i386 Architektur aktivieren
sudo dpkg --add-architecture i386

# Neue Repos manuell in /etc/apt/sources.list.d/ eintragen
# WICHTIG: signed-by=/usr/share/keyrings/ailinux-archive-keyring.gpg verwenden

# Update
sudo apt update
```

Siehe [CLIENT-SETUP.md](CLIENT-SETUP.md) für Details.

## Troubleshooting

### Problem: Mirror-Update schlägt fehl
**Lösung:**
```bash
# Container neustarten
docker compose restart apt-mirror

# Logs prüfen
docker compose logs --tail=100 apt-mirror

# Permissions fixen
./heal-perms.sh
```

### Problem: Signierung fehlgeschlagen
**Lösung:**
```bash
# GPG Keys importieren
./fix-keyring.sh

# Manuelle Signierung
./sign-repos.sh /path/to/specific/repo
```

### Problem: DEP-11 Metadata Fehler
**Lösung:**
```bash
# DEP-11 reparieren (safe)
./repair-dep11.sh

# Oder vollständige Heilung
./nova-heal.sh
```

### Problem: Disk Space voll während Sync
**Lösung:**
```bash
# Sync abbrechen (sicher)
docker compose exec apt-mirror killall apt-mirror

# Mirror-List reduzieren (siehe "Selektive Migration" oben)

# Alte Pakete cleanen
docker compose exec apt-mirror apt-mirror --cleanup-only

# Erneut starten
./update-mirror.sh
```

## Rollback Plan

Falls die neue Konfiguration Probleme macht:

```bash
# Backup wiederherstellen
sudo cp /home/zombie/ailinux-repo/repo/mirror/mirror.list.backup-YYYYMMDD \
        /home/zombie/ailinux-repo/repo/mirror/mirror.list

# Mirror auf alten Stand bringen
./update-mirror.sh

# Neue Repos aus Mirror entfernen (optional)
docker compose exec apt-mirror apt-mirror --cleanup-only
```

## Performance-Tipps

### Während des ersten Syncs:
- Lass den Server ungestört laufen (keine anderen Mirror-Updates)
- Prüfe Netzwerk-Bandbreite: `limit_rate` in mirror.list bei Bedarf reduzieren
- Monitor Disk I/O: `iostat -x 5` (falls installiert)

### Nach erfolgreichem Sync:
- Tägliche Updates via Cron laufen automatisch (3:00 AM)
- Deltas sind viel kleiner (~1-5 GB pro Tag)
- Health-Checks regelmäßig ausführen: `./health.sh` (wöchentlich)

## Weiterführende Informationen

- [CLIENT-SETUP.md](CLIENT-SETUP.md) - Detaillierte Client-Konfiguration
- [DEP11-AUTO-CLEANUP.md](DEP11-AUTO-CLEANUP.md) - Metadata-Verwaltung
- [CLAUDE.md](CLAUDE.md) - Vollständige Repository-Dokumentation

## Support

Bei Problemen:
1. Logs prüfen: `docker compose logs --tail=200 apt-mirror nginx`
2. Troubleshooting: `./troubleshoot.sh`
3. Health-Check: `./health.sh`
4. Self-Healing: `./nova-heal.sh`
