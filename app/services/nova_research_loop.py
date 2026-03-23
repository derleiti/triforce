"""
Nova Research Loop v1.0
========================
Code-Scan → Mail → Zombie-Reply → Implementation → Shadow-Test → Production
"""
from __future__ import annotations
import asyncio, hashlib, logging, re, time
from typing import Optional
logger = logging.getLogger("ailinux.research_loop")

RESEARCH_AGENT_PROMPT = """\
Du bist der TriForce Research-Agent. Analysiere den Codebase und entwickle Vorschläge.

AUFGABE:
1. Code scannen (code_tree, code_read, dev_analyze, dev_links)
2. Konkrete Verbesserungen, Bugs, Features identifizieren
3. Pro Finding: E-Mail an nova@ailinux.me schreiben

REGELN: Kein Code ändern. Nur Proposals. Kein git, kein shell.

E-MAIL FORMAT:
Betreff: [RESEARCH] <kurze Beschreibung>
Inhalt: Was gefunden | Warum wichtig | Konkrete Änderung (Datei + Zeile) | Risiko (low/mid/high) | Aufwand (klein/mittel/groß)

Nutze: mail_send(to="nova@ailinux.me", subject="[RESEARCH] ...", body="...")
Dann: TASK_COMPLETE
"""

IMPLEMENTATION_PROMPT_TEMPLATE = """\
Du bist der TriForce Implementation-Agent. Dieses Research-Proposal wurde genehmigt:

PROPOSAL: {subject}
ANMERKUNGEN: {notes}

WORKFLOW:
1. Code lesen (code_read, code_tree)
2. Auf zombie-pc (10.10.0.2) implementieren via remote_task / agent_call
3. Testen:
   - Syntax-Check: python3 -m py_compile <file>
   - Import-Check: python3 -c "import <module>"
   - Funktionstest wenn möglich
4. GRÜN → Production: git add + commit "feat: [RESEARCH-IMPL] {short_subject}" + push + restart
   → notify_send "✅ Deployed: {short_subject}"
5. ROT → KEIN Deploy, kein Push
   → notify_send "❌ Failed: {short_subject} — <Fehler>"
   → Änderungen rückgängig

SICHERHEIT: git status vor erstem Commit. Bei Unsicherheit: notify und warten.
Dann: TASK_COMPLETE
"""

_APPROVED = re.compile(r"\b(umsetzen|implement|ok|okay|ja|yes|do it|go ahead|approved|mach das|bauen|go)\b", re.I)
_SKIP     = re.compile(r"\b(skip|nein|no|nicht|later|später|ignore|ignorieren|abbrechen|cancel|nope)\b", re.I)
_AUTHORIZED_SENDERS = {"admin@ailinux.me","zombie@ailinux.me","markus@ailinux.me","derleiti@gmail.com"}

_sent: dict = {}
COOLDOWN = 86400 * 3

def _hash(s): return hashlib.sha1(s.lower().encode()).hexdigest()[:10]
def _already_sent(s): return (time.time() - _sent.get(_hash(s), 0)) < COOLDOWN
def _mark_sent(s): _sent[_hash(s)] = time.time()

def parse_reply(body: str) -> Optional[str]:
    b = body.strip().lower()[:500]
    if _APPROVED.search(b): return "implement"
    if _SKIP.search(b): return "skip"
    return None

async def handle_research_reply(subject: str, reply_body: str, sender: str) -> None:
    if sender.lower() not in _AUTHORIZED_SENDERS:
        logger.info(f"research_loop: Reply von {sender} ignoriert")
        return
    decision = parse_reply(reply_body)
    try:
        from ..mcp.notification_manager import create_notification as _cn
        if decision == "implement":
            logger.info(f"research_loop: APPROVED — {subject}")
            from .agent_spawner import get_agent_spawner
            short = subject.replace("[RESEARCH]","").strip()[:60]
            ctx = IMPLEMENTATION_PROMPT_TEMPLATE.format(
                subject=subject, notes=reply_body[:300],
                short_subject=short
            )
            sid = await get_agent_spawner().spawn_for_issue(
                issue_type="implementation_agent", context=ctx, source="research_loop"
            )
            _cn({"title": f"🔨 Implementation: {short}",
                 "body": f"Session: {sid}", "source": "system",
                 "priority": "normal", "tags": ["research", "implementation"]})
        elif decision == "skip":
            logger.info(f"research_loop: SKIPPED — {subject}")
            _mark_sent(subject)
            _cn({"title": f"⏭️ Research skipped: {subject[:60]}",
                 "body": "Archiviert — 3 Tage Cooldown.",
                 "source": "system", "priority": "low"})
        else:
            logger.info(f"research_loop: Keine klare Entscheidung in Reply für: {subject}")
    except Exception as e:
        logger.error(f"research_loop.handle_research_reply: {e}")

async def handle_admin_mail(subject: str, body: str) -> None:
    """Mails von admin@ → direkter Reply via generate_response + mail_send.

    KEIN Agent-Subprocess mehr — verhindert Anthropic-API-Rate-Limit-Ausfall.
    Nutzt internen Chat-Handler mit Fallback-Modellen (Ollama Cloud / OpenRouter).
    """
    try:
        from ..mcp.notification_manager import create_notification
        create_notification({
            "title": f"📬 Admin-Mail: {subject[:60]}",
            "body": f"Von: admin@ailinux.me\n\n{body[:500]}",
            "source": "system", "priority": "high",
            "tags": ["admin", "mail", "urgent"],
        })
        logger.info(f"research_loop: Admin-Mail empfangen: {subject[:60]}")

        # Schritt 1: Antwort direkt generieren (kein Agent-Subprocess, kein API-Limit)
        try:
            from ..services.chat import generate_response
            prompt = (
                f"Du bist Nova, der KI-Assistent von AILinux.\n"
                f"Du hast eine Mail von admin@ailinux.me erhalten.\n"
                f"Betreff: {subject}\n"
                f"Inhalt: {body[:2000]}\n\n"
                f"Antworte kurz, hilfreich und auf Deutsch. Maximal 5 Sätze."
            )
            # Bevorzuge Ollama Cloud (kein API-Limit), Fallback automatisch via chat.py
            reply_text = await generate_response(
                prompt,
                model="gpt-oss:cloud/120b",
                temperature=0.4,
                max_tokens=512,
            )
        except Exception as gen_err:
            logger.warning(f"research_loop.handle_admin_mail: generate_response fehlgeschlagen ({gen_err}), nutze Fallback-Text")
            reply_text = (
                f"Hallo,\n\ndeine Mail wurde empfangen (Betreff: {subject[:80]}).\n"
                f"Nova hat sie registriert und leitet sie weiter.\n\n"
                f"— Nova / AILinux"
            )

        # Schritt 2: mail_send direkt via MCP_HANDLERS (kein HTTP, kein Auth-Problem)
        try:
            from app.routes.mcp import MCP_HANDLERS
            mail_send = MCP_HANDLERS.get("mail_send")
            if mail_send:
                await mail_send({
                    "to": "admin@ailinux.me",
                    "subject": f"Re: {subject[:80]}",
                    "body": reply_text,
                })
                logger.info(f"research_loop: Admin-Mail-Reply direkt gesendet für: {subject[:60]}")
            else:
                logger.warning("research_loop.handle_admin_mail: mail_send handler nicht in MCP_HANDLERS")
        except Exception as send_err:
            logger.error(f"research_loop.handle_admin_mail: mail_send fehlgeschlagen: {send_err}")

    except Exception as e:
        logger.error(f"research_loop.handle_admin_mail: {e}")

async def run_daily_scan() -> None:
    logger.info("research_loop: Täglicher Scan startet")
    try:
        from .agent_spawner import get_agent_spawner
        await get_agent_spawner().spawn_for_issue(
            issue_type="research_agent",
            context=RESEARCH_AGENT_PROMPT + (
                "\n\nHeute: Analysiere app/routes/, app/services/, app/mcp/ auf:\n"
                "- Unbehandelte Exceptions\n- Performance-Hotspots\n"
                "- Missing Input-Validation\n- Agent-Integration Verbesserungen\n"
                "Pro Finding = separate Mail."
            ),
            source="daily_scheduler",
        )
    except Exception as e:
        logger.error(f"research_loop.run_daily_scan: {e}")

_processed_uids: set = set()
_last_mail_check = 0.0
_last_scan = 0.0
MAIL_CHECK_INTERVAL = 300
SCAN_INTERVAL = 86400
REDIS_KEY_PROCESSED_UIDS = "nova:mail:processed_uids"

def _load_processed_uids_from_redis() -> set:
    """Load processed mail UIDs from Redis for persistence across restarts."""
    try:
        import redis
        r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
        members = r.smembers(REDIS_KEY_PROCESSED_UIDS)
        return set(members) if members else set()
    except Exception as e:
        logger.warning(f"Redis load _processed_uids failed: {e}")
        return set()

def _save_uid_to_redis(uid: str) -> None:
    """Persist a processed UID to Redis."""
    try:
        import redis
        r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)
        r.sadd(REDIS_KEY_PROCESSED_UIDS, uid)
        r.expire(REDIS_KEY_PROCESSED_UIDS, 604800)  # 7 days TTL
    except Exception:
        pass

async def check_mail_replies() -> None:
    global _last_mail_check
    if time.time() - _last_mail_check < MAIL_CHECK_INTERVAL: return
    _last_mail_check = time.time()
    try:
        from app.routes.mcp import MCP_HANDLERS
        mail_inbox = MCP_HANDLERS.get("mail_inbox")
        if not mail_inbox:
            logger.debug("check_mail_replies: mail_inbox handler not found")
            return
        res = await mail_inbox({"limit": 20})
        if not res or res.get("error"):
            logger.debug(f"check_mail_replies: no result or error: {res}")
            return
        # Seed _processed_uids: first try Redis, then fallback to current inbox
        if not _processed_uids:
            redis_uids = _load_processed_uids_from_redis()
            if redis_uids:
                _processed_uids.update(redis_uids)
                logger.info(f"check_mail_replies: loaded {len(redis_uids)} UIDs from Redis")
            else:
                for m in res.get("messages", []):
                    uid = str(m.get("uid", ""))
                    _processed_uids.add(uid)
                    _save_uid_to_redis(uid)
                logger.info(f"check_mail_replies: seeded {len(_processed_uids)} existing UIDs to Redis")
            return
        new_mails = [m for m in res.get("messages", []) if str(m.get("uid","")) not in _processed_uids]
        logger.info(f"check_mail_replies: {len(new_mails)} new mails found")
        for mail in new_mails:
            uid = str(mail.get("uid",""))
            if uid in _processed_uids: continue
            subject = mail.get("subject","")
            sender  = mail.get("from","")
            # Research-Reply
            if "[research]" in subject.lower():
                mail_read = MCP_HANDLERS.get("mail_read")
                if not mail_read: continue
                rr = await mail_read({"uid": uid})
                if rr and not rr.get("error"):
                    body = rr.get("body","")
                    await handle_research_reply(subject, body, sender)
                    _processed_uids.add(uid)
                    _save_uid_to_redis(uid)
                    mark_seen = MCP_HANDLERS.get("mail_mark_seen")
                    if mark_seen: await mark_seen({"uid": uid})
            # Admin-Proposal
            elif "admin@ailinux.me" in sender.lower():
                mail_read = MCP_HANDLERS.get("mail_read")
                if not mail_read: continue
                rr = await mail_read({"uid": uid})
                if rr and not rr.get("error"):
                    body = rr.get("body","")
                    await handle_admin_mail(subject, body)
                    _processed_uids.add(uid)
                    _save_uid_to_redis(uid)
                    mark_seen = MCP_HANDLERS.get("mail_mark_seen")
                    if mark_seen: await mark_seen({"uid": uid})
    except Exception as e:
        logger.error(f"research_loop.check_mail_replies: {e}")

async def research_loop_tick() -> None:
    global _last_scan
    await check_mail_replies()
    if time.time() - _last_scan >= SCAN_INTERVAL:
        await run_daily_scan()
        _last_scan = time.time()
