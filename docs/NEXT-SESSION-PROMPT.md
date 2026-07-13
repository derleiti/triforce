# Folge-Prompt (Stand 2026-07-13, nach der venv/Leak/Shop-Session)

Kontext: Ich bin Markus (derleiti). TriForce laeuft auf Hetzner (Prod + Entwicklungsstufe),
zombie-pc ist die lokale Maschine (10.10.0.2, WireGuard). Am 13.07.2026 wurde in einer
langen Session der venv neu gebaut, ein oeffentliches Secret-Leck geschlossen und die
LemonSqueezy-/Entitlement-Kette repariert.

**Lies zuerst `docs/SESSION-2026-07-13.md` im Repo** - da steht alles Erledigte drin,
inkl. Commits, Backups und Begruendungen. Diese Datei ist die Kurzfassung fuer den Rest.

---

## ARBEITSREGELN (wichtig, aus Fehlern der letzten Session)

1. **Der MCP-Server IST TriForce.** `systemctl stop/restart triforce` aus einer MCP-Shell
   killt den eigenen Prozess (SIGTERM) und bricht die laufende Befehlskette ab.
   Immer stattdessen:
   `sudo systemd-run --on-active=5 --unit=tf-restart-$(date +%s) /bin/systemctl restart triforce`
2. **Ursache vor Fix. Planung vor Code. Bild vor Detail.** Nicht raten, wenn pruefbar.
3. **Vor jedem Eingriff ein Backup.** Zielordner: `~/triforce/.backups/`
4. **Nichts loeschen, was ich nicht ausdruecklich freigegeben habe.** Kein `rm -rf`,
   kein `git reset --hard`, kein `git stash drop`, kein `--delete`-rsync ohne Rueckfrage.
5. **Meine uncommitteten Dateien sind meine Arbeit - nicht anfassen, nicht committen,
   nicht wegstashen.** (Aktuell: `.gitignore`, `app/utils/system_log_collector.py`,
   `scripts/tools/nova_log_monitor.py`, `scripts/rotate-proxy-token.sh`,
   `scripts/tools/archive/`)
6. **Erfolg messen, nicht annehmen.** HTTP 200 und `ok:true` beweisen nichts.
   Immer den tatsaechlich gespeicherten Endzustand pruefen.
7. **Secrets niemals im Klartext ausgeben** - auch nicht in Debug-Output. Maskieren oder
   Pruefsummen vergleichen.
8. Ausgabe auf Deutsch, nummerierte Schritte bei Komplexem.

---

## PRIORITAET 1 - SICHERHEIT (offen, dringend)

**Alle 34 Secrets aus `config/triforce.env` rotieren.**
Die Datei war bis 13.07. oeffentlich unter
`https://ailinux.me/wp-content/plugins/nova-ai-frontend/config/triforce.env`
mit HTTP 200 abrufbar (578 Zeilen, Last-Modified 17. Juni, Expositionsdauer unbekannt),
zusaetzlich im Cloudflare-Cache. Das Leck ist geschlossen (Apache-Deny + Datei aus dem
Webroot entfernt), aber die Werte gelten als kompromittiert.

Reihenfolge:
1. LemonSqueezy API-Key + Webhook-Secret (sonst: gefaelschte `order_created`-Events
   -> Gratis-Lizenzen)
2. `NOVA_AI_INTERNAL_KEY` - **muss identisch mit `INTERNAL_API_KEY` bleiben**, sonst
   brechen alle `/v1/frontend/dashboard/*` mit 403
3. `NOVA_MCP_PASS`
4. restliche Eintraege durchgehen

Nach der Rotation: `docker compose up -d wordpress_fpm` + TriForce neu starten (Regel 1).

Zusaetzlich pruefen: Sind ausser `triforce.env` weitere sensible Dateien im Webroot?
`~/triforce/.backups/` enthaelt Secrets (chmod 600) - beim Aufraeumen daran denken.

---

## PRIORITAET 2 - COPA OCR GO-LIVE

Die Kette ist repariert und Ende-zu-Ende verifiziert:
`Checkout (signierte Custom-URL mit wp_user_id) -> Webhook (HMAC-SHA256)
-> Mapping 970007 -> copa_ocr -> Account nova_entitlements {"copa_ocr": true}`

Offen:
- [ ] LemonSqueezy: Produkt steht auf `test_mode=1` -> auf Live umstellen, Live-API-Key holen
      (Live- und Test-Keys sind verschieden)
- [ ] `NOVA_LS_TEST_MODE=false` in `config/triforce.env`, dann `docker compose up -d wordpress_fpm`
- [ ] Webhook-URL im LS-Dashboard eintragen:
      `https://ailinux.me/wp-json/nova-ai/v1/payments/webhook/lemonsqueezy`
- [ ] Echten Testkauf (LS-Testkarte), danach Account pruefen
- [ ] Demo-Modus in Copa OCR abschalten

Verifikationsbefehle stehen in `docs/SESSION-2026-07-13.md`.

---

## PRIORITAET 3 - ZOMBIE-PC GIT SORTIEREN (heikel, nichts ueberfahren)

Zustand: `ahead 6, behind 117`, **197 uncommittete Dateien**.
- 157 davon sind **reine chmod-Mode-Changes** (Rauschen, entstanden durch den alten
  `rsync -a --delete` des node-sync, der direkt ins Git-Arbeitsverzeichnis synchronisierte)
- 55 Dateien mit echtem Inhalt (grosse Loeschungen alter `.bak`/`.REMOVED`-Leichen)
- **8 untrackte Dateien mit echter Arbeit**: `mcp-auth-proxy.py`, `app/services/orcid.py`,
  `scripts/tools/nova_forum_watchdog.py` u.a. - **diese zuerst sichern**
- Ein Doppel-Commit: `ad181cc3` und `bed18f10`, identische Message

Der `triforce-node-sync.timer` ist auf zombie-pc bereits disabled. Beim Wiederaufsetzen:
**nie mit `rsync --delete` in ein Git-Arbeitsverzeichnis.** Nodes brauchen ein Deploy-Ziel
(z.B. `/opt/triforce`), kein Dev-Checkout.

Vorgehen: erst die 8 untrackten Dateien sichern, dann Mode-Changes vom Inhalt trennen,
dann entscheiden. Kein `reset --hard`.

---

## PRIORITAET 4 - KLEINERE BAUSTELLEN

- [ ] Meine 4 uncommitteten Dateien auf Hetzner (Log-Baustelle vom 12.07.) durchsehen
      und committen - **ich entscheide, was rein soll**
- [ ] Stashes vom 19.06. pruefen und dann entsorgen:
      - `stash@{2}`: Shop/Auth-Arbeit, 6 von 7 Dateien sind heute identisch im Repo,
        die verlorene TEST_MODE-Zeile ist wiederhergestellt -> **kann weg**
      - `stash@{1}`: 59 Dateien, u.a. `login/index.html` (1806 Zeilen) -> **vor dem
        Loeschen durchsehen**
- [ ] `app/routes/txt2img.py` importiert `comfy_client` - existiert nirgends im Repo.
      Route ist tot (schon vor der Session). Entweder Modul nachliefern oder Route entfernen.
- [ ] `.github/dependabot.yml`: `pytest*` in eine `groups`-Definition, sonst reisst der
      naechste Major dieselbe Luecke wieder auf (pytest 9 vs. pytest-asyncio <9).
- [ ] Federation: `Connection error to zombie-pc: [Errno 111] Connection refused` im Log.
      Ursache: zombie-pc erreicht Hetzner per SSH nicht mehr (Key nicht mehr in
      authorized_keys). Bewusst so oder reparieren? -> entscheiden.
- [ ] `wp-config.php` ist gitignored (enthaelt Secrets, korrekt so), aber die heutigen
      Aenderungen liegen nur auf der Platte. Backup: `~/triforce/.backups/`.
      Ueberlegen: Secrets raus, Datei versionierbar machen?
- [ ] `~/triforce/.venv.bak-*` und `.venv.old` auf zombie-pc aufraeumen, falls noch da
- [ ] Aeltere TODOs: DMARC von `p=quarantine pct=25` auf `pct=100`, dann `p=reject`.
      Backup-Server (5.104.107.103) laeuft nur bis ~April 2027 -> Migration planen.

---

## WAS BEREITS ERLEDIGT IST (nicht nochmal machen)

- venv Hetzner: 5.9 GB / 218 Pakete -> 648 MB / 114 Pakete, 178 Tests gruen
  (torch/CUDA/transformers/chromadb/crawlee/python-jose/passlib/tenacity raus -
  alle ungenutzt oder lazy hinter try/except)
- venv zombie-pc: neu gebaut, `pydantic>=2.13` (alter Pin 2.11.10 hatte kein cp314-Wheel)
- `requirements.txt`: `a` (Tippfehler) raus, `aiofiles`/`fakeredis`/`requests`/`PyYAML`/
  `cryptography`/`rich`/`textual`/`orjson` ergaenzt (wurden hart importiert, nie deklariert)
- Secret-Leck geschlossen: Apache-Deny-Snippet, CF-Cache gepurgt, Dateien aus dem Webroot
- Auto-Update auf Hetzner strukturell aus (`/etc/systemd/system-preset/10-triforce-no-autoupdate.preset`)
- node-sync auf zombie-pc disabled (war seit 05.06. defekt, 10.356 lautlose Fehlversuche)
- Shop/Entitlements: 3 Brueche repariert (fehlender Auth-Header + `blocking=false`;
  `INTERNAL_API_KEY` fehlte in `_allowed_secrets()`; `UserUpsertPayload` hatte kein Feld
  `extra` -> pydantic verwarf Kaeufe still). Commits `c1278305`, `cb64b9aa`.
