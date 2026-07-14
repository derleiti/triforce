# Folge-Prompt — TriForce / AILinux (Stand 2026-07-14, 18:40)

Ich bin Markus (derleiti). TriForce laeuft auf Hetzner (Prod + Entwicklungsstufe),
zombie-pc ist die lokale Maschine (10.10.0.2, WireGuard).

Am 13.07.2026 lief eine lange Session: venv neu gebaut, oeffentliches Secret-Leck
geschlossen, LemonSqueezy-/Entitlement-Kette repariert.
Am 14.07.2026 wurden drei Regressionen daraus geschlossen (uvloop-Verlust,
ImportError im Gemini-Key-Resolver, kaputte dependabot.yml).
**Lies zuerst `docs/SESSION-2026-07-13.md` und `docs/SESSION-2026-07-14.md`** —
dort steht alles Erledigte mit Commits, Backups und Begruendungen.

> **Offen und wichtig:** Der Restart, der uvloop scharf schaltet, steht noch aus.
> Regel 1 beachten — niemals `systemctl restart triforce` direkt aus einer MCP-Shell.

---

## ARBEITSREGELN (aus konkreten Fehlern entstanden — bitte einhalten)

1. **Der MCP-Server IST TriForce.** `systemctl stop/restart triforce` aus einer
   MCP-Shell killt den eigenen Prozess (SIGTERM) und bricht die Befehlskette ab.
   Immer: `sudo systemd-run --on-active=5 --unit=tf-restart-$(date +%s) /bin/systemctl restart triforce`
2. **Ursache vor Fix. Planung vor Code.** Nicht raten, wenn pruefbar.
3. **Backup vor jedem Eingriff** nach `~/triforce/.backups/`
4. **Nichts loeschen ohne meine ausdrueckliche Freigabe.** Kein `rm -rf`,
   kein `reset --hard`, kein `stash drop`, kein `stash pop`, kein `rsync --delete`.
5. **Meine uncommitteten Dateien sind meine Arbeit** — nicht anfassen, nicht
   committen, nicht wegstashen.
6. **Erfolg messen, nicht annehmen.** HTTP 200 und `ok:true` beweisen nichts.
   Immer den tatsaechlich gespeicherten Endzustand pruefen.
   (Das Backend hat Kaeufe monatelang mit `ok:true` quittiert und weggeworfen.)
7. **Secrets nie im Klartext ausgeben**, auch nicht im Debug-Output. Maskieren
   oder Pruefsummen vergleichen.
8. **Vor Aenderungen an WordPress/Shop: mu-plugins pruefen.** Sie werden zwangs-
   geladen und ueberschreiben Plugin-Routen per `rest_pre_dispatch`.
9. Deutsch, nummerierte Schritte bei Komplexem.

---

## PRIORITAET 1 — SECRETS ROTIEREN (offen, dringend)

Alle 34 Secrets aus `config/triforce.env` gelten als kompromittiert. Die Datei war
bis 13.07. oeffentlich abrufbar (HTTP 200, 578 Zeilen, Last-Modified 17. Juni,
Expositionsdauer unbekannt), zusaetzlich im Cloudflare-Cache.
Das Leck ist geschlossen — die Werte bleiben verbrannt.

Reihenfolge:
1. LemonSqueezy API-Key + Webhook-Secret
   (kompromittierter Webhook-Secret = gefaelschte `order_created`-Events = Gratis-Lizenzen)
2. `NOVA_AI_INTERNAL_KEY` — **muss identisch mit `INTERNAL_API_KEY` bleiben**,
   sonst 403 auf allen `/v1/frontend/dashboard/*`
3. `NOVA_MCP_PASS`
4. `OLLAMA_API_KEY` — stand am 14.07. im Klartext in einem Chat-Log
   (kam aus `/etc/systemd/system/ollama.service.d/api-key.conf`)
5. Rest durchgehen

Danach: `docker compose up -d wordpress_fpm` + TriForce neu starten (Regel 1).

---

## PRIORITAET 2 — COPA OCR GO-LIVE

Die Kette ist repariert und Ende-zu-Ende verifiziert:
`Checkout -> Webhook (HMAC-SHA256) -> Mapping 970007 -> copa_ocr -> Account {"copa_ocr": true}`

Offen:
- [ ] LS-Produkt steht auf `test_mode=1` -> auf Live (Live-Keys sind andere Keys)
- [ ] `NOVA_LS_TEST_MODE=false` in `config/triforce.env`
- [ ] Webhook-URL im LS-Dashboard:
      `https://ailinux.me/wp-json/nova-ai/v1/payments/webhook/lemonsqueezy`
- [ ] Echter Testkauf -> Account pruefen
- [ ] Demo-Modus in Copa OCR aus

### ENTSCHEIDUNG offen: mu-plugin `ailinux-nova-checkout-override.php`

Dieses mu-plugin kapert `/nova-ai/v1/shop/checkout` per `rest_pre_dispatch` und
liefert den generischen **`buy_now_url` statt des Custom-Checkouts**. Es stammt vom
29.06. und war offensichtlich ein Workaround fuer den `variant_id`-Bug — **der ist
seit 13.07. gefixt** (Commit `cb64b9aa`), der Override also technisch ueberfluessig.

Konsequenz heute: Der Kauf traegt **kein `wp_user_id`**. Die Zuordnung laeuft ueber
`resolve_user_id($hint, $email)` -> Fallback `email_exists()`.
**Das funktioniert nur, wenn die Zahlungs-E-Mail der Account-E-Mail entspricht.**
Zahlt jemand mit anderer Adresse (PayPal, Firmenmail, Tippfehler): `user_id = 0`,
Log-Warnung "Could not resolve WP user", **bezahlt ohne Lizenz**.

Der Custom-Checkout ist geprueft nutzbar (URL liefert HTTP 200).
Vorschlag: **nach** der Key-Rotation, noch im LS-Testmodus, den Override deaktivieren,
einen Testkauf mit abweichender E-Mail durchfuehren und pruefen, ob das Entitlement
trotzdem ankommt. Wenn ja -> Override endgueltig raus. **Nicht kurz vor dem Go-Live
ungetestet umstellen.**

---

## PRIORITAET 3 — ZOMBIE-PC GIT SORTIEREN (heikel)

`ahead 6, behind 117`, 197 uncommittete Dateien:
- 157 reine chmod-Mode-Changes (Rauschen vom alten `rsync -a --delete` des node-sync,
  der direkt ins Git-Arbeitsverzeichnis synchronisierte)
- 55 mit echtem Inhalt (grosse Loeschungen alter `.bak`/`.REMOVED`-Leichen)
- **8 untrackte Dateien mit echter Arbeit** (`mcp-auth-proxy.py`,
  `app/services/orcid.py`, `scripts/tools/nova_forum_watchdog.py` u.a.) -> zuerst sichern
- Doppel-Commit `ad181cc3` / `bed18f10` (identische Message)

`triforce-node-sync.timer` ist bereits disabled. Beim Wiederaufsetzen: **nie mit
`--delete` in ein Git-Arbeitsverzeichnis** — Nodes brauchen ein Deploy-Ziel
(z.B. `/opt/triforce`), kein Dev-Checkout.

Vorgehen: untrackte Dateien sichern -> Mode-Changes vom Inhalt trennen -> entscheiden.
Kein `reset --hard`.

**UNGEKLAERT:** Am 12.07. um 22:36/22:37 hat etwas auf zombie-pc `.env.example` und
`app/mcp/tool_registry_unified.py` geschrieben. Der node-sync war zu dem Zeitpunkt
seit 5 Wochen tot, kann es also nicht gewesen sein. Wenn ich (Markus) das nicht selbst
war: herausfinden, was dort schreibt.

---

## PRIORITAET 4 — STASHES (4 Stueck, NICHT blind poppen)

- `stash@{0}` "compose wip" (11.07.): enthaelt exakt die compose-Reparatur, die am
  13.07. vollstaendig umgesetzt wurde -> **redundant**. ACHTUNG: der Stash **loescht
  nebenbei den Volume-Mount** `/var/www/update.ailinux.me`. Ein `pop` wuerde
  update.ailinux.me aushaengen. -> pruefen, dann verwerfen.
- `stash@{1}` (19.06., auto-stash): 59 Dateien, u.a. `login/index.html` (1806 Zeilen).
  -> **vor dem Loeschen durchsehen**
- `stash@{2}` (19.06., auto-stash): Shop/Auth-Arbeit. 6 von 7 Dateien sind heute
  identisch im Repo, die verlorene TEST_MODE-Zeile ist wiederhergestellt. -> **kann weg**
- `stash@{3}` "wip-before-rebase" (05.06.): 11 Dateien, u.a.
  `docker/wordpress/search-root/index.html` (2221 Zeilen geaendert) + vhost-search.conf
  -> **durchsehen, das ist echte Arbeit**

`rescue/master-failed-merge-20260619-174248`: **0 eigene Commits** -> nichts verloren,
Branch kann geloescht werden.

---

## PRIORITAET 5 — KLEINERES

### Erledigt am 14.07. (nicht wiederholen)
- [x] `.github/dependabot.yml` — stand mit `package-ecosystem: ""` da (unausgefuellte
      GitHub-Vorlage, ungueltig). Neu: pip + github-actions, Gruppen fuer pytest/server/linters.
- [x] uvloop/httptools/watchfiles waren seit dem 13.07. **deinstalliert** — `google-antigravity`
      fordert nacktes `uvicorn` und hat die `[standard]`-Extras verdraengt. Wiederhergestellt,
      requirements.txt haelt jetzt `uvicorn[standard]>=0.51` fest.
- [x] `resolve_gemini_api_key()` warf `ImportError` (`from ..config import settings` —
      existiert nicht, nur `get_settings()`). Jede Gemini-Vision-Anfrage crashte damit.

### Offen
- [ ] **Vault ist gesperrt** (`vault_keys` → "Vault is locked"). Deshalb loest
      `GEMINI_API_KEY` **nirgends** auf: nicht in `.env`, nicht in `config/triforce.env`,
      nicht in der Prozess-Env, kein `.secrets.json`. -> Vault entsperren oder Key in die Env.
      Das ist die zweite Haelfte der Gemini-401s.
- [ ] **`prometheus_fastapi_instrumentator` fehlt** im venv. `app/main.py:28` importiert es
      hinter `try/except` -> Metriken sind still aus. Nachziehen oder bewusst rauswerfen.
- [ ] **Drei Tool-Registries** (v3/v4/v5) laufen laut Chat vom 13.07. parallel, die SSE-Route
      lieferte 145 Tools aus unklarer vierter Quelle. Noch nicht verifiziert.
- [ ] **`wp-config.php` enthaelt Secrets im Klartext** (`NOVA_AI_INTERNAL_KEY`,
      `NOVA_MCP_PASS` hartkodiert). Datei ist gitignored — korrekt, aber die
      Aenderungen liegen nur auf Platte. Besser: Werte per `getenv()` aus der
      Container-Env ziehen (wie `NOVA_LS_*`), dann ist die Datei secret-frei.
- [ ] 4 uncommittete Dateien auf Hetzner (Log-Baustelle 12.07., 22:08) durchsehen
      und committen — **Markus entscheidet, was rein soll**. Dazu neu: untrackter
      Ordner `scripts/tools/archive/` mit `fix-mcp-access.sh` (11.07.).
- [ ] 7 verbliebene `.bak`-Dateien im Webroot (themes/, mu-plugins/). Alle liefern 403,
      sollten aber trotzdem raus — die Deny-Regel ist eine Fehlkonfiguration vom
      Wegfallen entfernt.
- [ ] `app/routes/txt2img.py` importiert `comfy_client` — existiert nicht.
      **Geprueft am 14.07.: die Route ist in `main.py` nirgends registriert**, der Import
      laeuft nie, der Code ist tot und harmlos. Entfernen oder Modul nachliefern —
      Entscheidung offen, kein Zeitdruck.
- [ ] `hardware_accel.get_uvicorn_config()` meldet hart `loop="uvloop"` / `http="httptools"`,
      obwohl die Werte nie an uvicorn gehen (nur `to_dict()` liest sie). Kosmetik, aber
      irrefuehrend — die Diagnose hat am 13.07. genau deshalb daneben gezeigt.
- [ ] **Ollama:** laeuft auf beiden Nodes korrekt (0.0.0.0:11434, enabled). Aber die Unit
      haengt an `WantedBy=default.target` statt `multi-user.target` — bricht, sobald
      jemand `set-default multi-user` setzt. Port **11435 (IPEX-LLM / Intel iGPU) ist tot** (HTTP 000).
- [ ] Federation: `Connection error to zombie-pc: [Errno 111] Connection refused`.
      zombie-pc erreicht Hetzner per SSH nicht mehr (Key nicht in authorized_keys).
      Bewusst so oder reparieren? -> entscheiden.
- [ ] `~/triforce/.backups/` enthaelt Secrets (chmod 600) — beim Aufraeumen daran denken.
- [ ] DMARC: `pct=25` -> `100` -> `p=reject`.
      Backup-Server (5.104.107.103) laeuft nur bis ~April 2027 -> Migration planen.

## BEREITS ERLEDIGT (nicht wiederholen)

- **venv Hetzner**: 5.9 GB / 218 Pakete -> 648 MB / 114 Pakete, 178 Tests gruen.
  Raus: torch, CUDA, transformers, sentence-transformers, onnxruntime, chromadb,
  llama-index, crawlee, python-jose, passlib, tenacity (ungenutzt oder lazy hinter
  try/except). Rein: aiofiles, requests, PyYAML, cryptography, rich, textual, orjson,
  fakeredis (wurden hart importiert, waren nie deklariert).
- **venv zombie-pc** neu gebaut (`pydantic>=2.13`; alter Pin 2.11.10 hatte kein
  cp314-Wheel -> Rust-Build -> PyO3 kann kein Python 3.14).
- **requirements.txt**: Zeile `a` entfernt (Tippfehler aus Merge-Resolve, zog ein
  fremdes PyPI-Paket), pytest-asyncio 1.2.0 -> 1.3.0.
- **Secret-Leck geschlossen**: Apache-Deny-Snippet (`AllowOverride` ist aus, .htaccess
  greift nicht), Cloudflare-Cache gepurgt, 34 sensible Dateien aus dem Webroot entfernt.
  ACME-Challenge geprueft: funktioniert weiter (Certs gueltig bis 04.09.).
- **Auto-Update Hetzner strukturell aus**
  (`/etc/systemd/system-preset/10-triforce-no-autoupdate.preset`). Am 19.06. hatte
  `auto-stash` + `hard reset` uncommittete Arbeit weggeraeumt.
- **node-sync zombie-pc disabled** (seit 05.06. defekt, 10.356 lautlose Fehlversuche
  mit `exit 0`).
- **Shop/Entitlements repariert** (Commits `c1278305`, `cb64b9aa`):
  fehlender Auth-Header + `blocking=false` -> 401 unsichtbar;
  `INTERNAL_API_KEY` fehlte in `_allowed_secrets()`;
  `UserUpsertPayload` hatte kein Feld `extra` -> pydantic verwarf Kaeufe still;
  `ShopService`: Produkt-ID aus `attributes.product_id` statt
  `relationships.product.data.id` (LS liefert dort nur `.links`).
  Auth am Endpunkt verifiziert: 401 ohne Key, 401 mit falschem Key.
