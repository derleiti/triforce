# DEP-11 Automatische Bereinigung

## Was wurde geändert?

Das Repository-Mirror-System wurde erweitert, um **unreparierbare DEP-11 Metadaten-Dateien automatisch zu entfernen**. Dies verhindert Hash-Fehler auf Client-Seite.

## Problem

Wenn DEP-11 Dateien (AppStream-Metadaten wie Icons) auf dem Mirror beschädigt sind und nicht vom Upstream neu geladen werden können, verursachen sie Hash-Fehler beim Client:

```
Fehl:18 https://repo.ailinux.me:8443/mirror/... Hash-Summe stimmt nicht überein
```

## Lösung

Das System führt nun automatisch folgende Schritte durch:

### 1. Validierung (`postmirror.sh`)

Nach jedem `apt-mirror` Lauf:
- Prüft alle DEP-11 Dateien gegen ihre SHA256-Hashes in den Release-Dateien
- Versucht fehlende/korrupte Dateien vom Upstream neu zu laden
- **NEU:** Entfernt Dateien, die nicht repariert werden können

### 2. Neu-Signierung (`sign-repos.sh`)

Nach der DEP-11 Validierung:
- Generiert neue Release-Dateien mit `apt-ftparchive release`
- `apt-ftparchive` scannt nur **existierende** Dateien
- Entfernte DEP-11 Dateien erscheinen nicht mehr in der Release-Datei
- Signiert die neue Release-Datei mit dem AILinux GPG-Schlüssel

### 3. Ergebnis

- Clients sehen **keine Hash-Fehler** mehr
- Fehlende DEP-11 Metadaten sind **nicht kritisch** - das Repository funktioniert
- Nur AppStream-Features (Software-Center Icons, Beschreibungen) können fehlen

## Workflow

```
apt-mirror (synchronisiert Pakete)
    ↓
postmirror.sh
    ├─ Validiert DEP-11 Dateien gegen SHA256 Hashes
    ├─ Lädt fehlende/korrupte Dateien vom Upstream nach
    └─ ENTFERNT Dateien, die nicht nachgeladen werden können
    ↓
repair-dep11.sh (zusätzliche Reparaturversuche)
    ├─ Versucht fehlende DEP-11 Dateien erneut zu laden
    └─ Validiert heruntergeladene Dateien
    ↓
remove-unrepairable-dep11.sh (NEU!)
    ├─ Prüft ALLE DEP-11 Dateien gegen Release-Hashes
    ├─ Identifiziert Dateien mit Hash-Mismatches
    └─ ENTFERNT unreparierbare Dateien
    ↓
sign-repos.sh (wird automatisch von postmirror.sh aufgerufen)
    ├─ Generiert neue Release-Datei mit apt-ftparchive
    ├─ Nur existierende Dateien werden in Release eingetragen
    └─ Signiert mit AILinux GPG-Schlüssel
    ↓
Fertig - Repository ist konsistent und client-ready
```

## Änderungen im Code

### NEU: `remove-unrepairable-dep11.sh`

Komplett neues Script, das:
- Alle Release-Dateien im Mirror durchsucht
- SHA256-Hashes aus Release-Dateien parst
- Jede DEP-11 Datei gegen ihren erwarteten Hash validiert
- Dateien mit Hash-Mismatches entfernt
- Detaillierte Logs erstellt

**Verwendung:**
```bash
# Automatisch in update-mirror.sh integriert
./update-mirror.sh

# Oder manuell
./remove-unrepairable-dep11.sh
```

### `update-mirror.sh` (Zeilen 20, 72-77, 89-90)

**Hinzugefügt:**
```bash
REMOVE_UNREPAIRABLE_DEP11_PATH="${REMOVE_UNREPAIRABLE_DEP11_PATH:-/var/spool/apt-mirror/var/remove-unrepairable-dep11.sh}"

# Container-Modus:
log "Entferne unreparierbare DEP-11 Dateien…"
if [ -x "$REMOVE_UNREPAIRABLE_DEP11_PATH" ]; then
  bash -lc "$REMOVE_UNREPAIRABLE_DEP11_PATH" || log "Unrepairable-DEP-11-Cleanup abgeschlossen"
else
  log "WARN: remove-unrepairable-dep11.sh nicht gefunden"
fi

# Host-Modus:
"${COMPOSE_CMD[@]}" exec -T "$SERVICE" bash -c "[ -x '${REMOVE_UNREPAIRABLE_DEP11_PATH}' ] && bash '${REMOVE_UNREPAIRABLE_DEP11_PATH}' || true"
```

Dieser Schritt läuft **nach** repair-dep11.sh und **vor** dem finalen Abschluss.

### `postmirror.sh` (Zeile 298-302)

```bash
else
  log "   ⚠ Konnte DEP-11 nicht aktualisieren – ENTFERNE korrupte Datei: ..."
  # Wichtig: Auch entfernen wenn nicht reparierbar, damit Clients nicht fehlerhaften Hash sehen
  rm -f "$tgt"
  ((rel_failed++))
  action="refresh_fail_removed"
fi
```

**Vorher:** Warnung ausgeben, fehlerhafte Datei bleibt bestehen
**Nachher:** Warnung ausgeben, fehlerhafte Datei **wird entfernt**

### `postmirror.sh` (Zeile 320-328)

```bash
log "✓ DEP-11 Validierung abgeschlossen: $CLEANED repariert, $FAILED entfernt (unreparierbar), ..."

if [[ $FAILED -gt 0 ]]; then
  log "⚠ $FAILED unreparierbare DEP-11 Dateien wurden entfernt"
  log "Repository wird im nächsten Schritt neu signiert (sign-repos.sh)"
fi
```

**Vorher:** Nur Statistik
**Nachher:** Explizite Warnung über entfernte Dateien + Hinweis auf Neu-Signierung

## Verwendung

### Automatisch (Empfohlen)

Einfach `update-mirror.sh` ausführen:

```bash
./update-mirror.sh
```

Das System führt automatisch aus:
1. `apt-mirror` - Synchronisiert Pakete
2. `postmirror.sh` - Validiert und bereinigt DEP-11 Dateien
3. `sign-repos.sh` - Signiert Repositories neu
4. `repair-dep11.sh` - Weitere Reparaturversuche (optional)

### Manuell (für Tests)

```bash
# Nur DEP-11 Validierung
cd /home/zombie/ailinux-repo
docker compose exec apt-mirror bash /var/spool/apt-mirror/var/postmirror.sh

# Nur Signierung
docker compose exec apt-mirror bash /var/spool/apt-mirror/var/sign-repos.sh /path/to/repo

# Vollständiges Update
./update-mirror.sh
```

## Installation der Änderungen

### Schritt 1: Container-Scripte aktualisieren

Die Änderungen wurden in `/home/zombie/ailinux-repo/postmirror.sh` vorgenommen.

Um sie im Container verfügbar zu machen:

```bash
cd /home/zombie/ailinux-repo
sudo ./fix-container-scripts-perms.sh
```

Oder manuell:

```bash
sudo cp postmirror.sh repo/var/postmirror.sh
sudo cp sign-repos.sh repo/var/sign-repos.sh
sudo cp repair-dep11.sh repo/var/repair-dep11.sh
sudo chmod +x repo/var/*.sh
```

### Schritt 2: Container neu starten

```bash
docker compose restart apt-mirror
```

### Schritt 3: Test

```bash
./update-mirror.sh
```

Überprüfen Sie die Logs:

```bash
tail -100 log/update-mirror.log
tail -100 /var/log/ailinux/postmirror.log  # im Container
```

## Verifizierung

### Server-Seite

```bash
# Prüfe DEP-11 Dateien manuell
./check-dep11-hashes.sh

# Oder mit remove-bad-dep11.sh
./remove-bad-dep11.sh
```

### Client-Seite

Wenn Clients immer noch Hash-Fehler sehen, liegt es an **Client-Caching**:

```bash
# Auf dem Client ausführen:
sudo rm -rf /var/lib/apt/lists/*
sudo apt update
```

## Logs

- `/home/zombie/ailinux-repo/log/update-mirror.log` - Haupt-Update-Log
- `/var/log/ailinux/postmirror.log` - DEP-11 Validierung (im Container)
- `/home/zombie/ailinux-repo/log/remove-bad-dep11.log` - Manuelle Validierung

## Wichtige Hinweise

1. **DEP-11 ist nicht kritisch**: Fehlende AppStream-Metadaten brechen das Repository nicht
2. **Clients cachen aggressiv**: Nach Server-Änderungen immer Client-Cache leeren
3. **Automatisch bei jedem Update**: System läuft bei jedem `update-mirror.sh` Aufruf
4. **Logs prüfen**: Bei Problemen immer zuerst die Logs ansehen

## Nächste Schritte

Nach der Installation:

1. Führen Sie `update-mirror.sh` einmal manuell aus
2. Überprüfen Sie die Logs auf Fehler
3. Testen Sie vom Client aus: `apt update`
4. Bei Client-Fehlern: APT-Cache leeren (siehe oben)

## Support

Bei Problemen:

```bash
# Automatische Diagnose
./troubleshoot.sh

# Umfassender Health-Check
./health.sh

# Repository-Signaturen prüfen
./repo-health.sh

# DEP-11 manuell validieren
./check-dep11-hashes.sh
```
