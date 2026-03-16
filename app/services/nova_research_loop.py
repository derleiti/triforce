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
        from ..mcp.structured_admin import handler as h
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
            await h({"method":"tools/call","params":{"name":"notify_send","arguments":{
                "title": f"🔨 Implementation: {short}",
                "body": f"Session: {sid}",
                "source":"system","priority":"normal","tags":["research","implementation"],
            }}})
        elif decision == "skip":
            logger.info(f"research_loop: SKIPPED — {subject}")
            _mark_sent(subject)
            await h({"method":"tools/call","params":{"name":"notify_send","arguments":{
                "title": f"⏭️ Research skipped: {subject[:60]}",
                "body": "Archiviert — 3 Tage Cooldown.",
                "source":"system","priority":"low","auto_resolve":True,
            }}})
        else:
            logger.info(f"research_loop: Keine klare Entscheidung in Reply für: {subject}")
    except Exception as e:
        logger.error(f"research_loop.handle_research_reply: {e}")

async def handle_admin_mail(subject: str, body: str) -> None:
    """Mails von admin@ → Forum-Proposal."""
    try:
        from ..mcp.structured_admin import handler as h
        content = (
            f"**📬 Admin Proposal**\n\n**Betreff:** {subject}\n\n"
            f"**Inhalt:**\n{body[:1000]}\n\n---\n"
            "*Automatisch erstellter Vorschlag. Zombie entscheidet.*"
        )
        await h({"method":"tools/call","params":{"name":"flarum_discussion_create","arguments":{
            "title": f"[PROPOSAL] {subject[:80]}", "content": content,
        }}})
        await h({"method":"tools/call","params":{"name":"notify_send","arguments":{
            "title": f"📬 Admin-Proposal: {subject[:60]}",
            "body": "Neuer Vorschlag im Forum. Deine Entscheidung.",
            "source":"system","priority":"normal","tags":["admin","proposal"],
        }}})
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

async def check_mail_replies() -> None:
    global _last_mail_check
    if time.time() - _last_mail_check < MAIL_CHECK_INTERVAL: return
    _last_mail_check = time.time()
    try:
        from ..mcp.structured_admin import handler as h
        res = await h({"method":"tools/call","params":{"name":"mail_inbox","arguments":{"limit":20}}})
        if not res or res.get("error"): return
        for mail in (res.get("result") or {}).get("messages", []):
            uid = str(mail.get("uid",""))
            if uid in _processed_uids: continue
            subject = mail.get("subject","")
            sender  = mail.get("from","")
            # Research-Reply
            if "[research]" in subject.lower() and not mail.get("seen", True):
                rr = await h({"method":"tools/call","params":{"name":"mail_read","arguments":{"uid":uid}}})
                if rr and not rr.get("error"):
                    body = (rr.get("result") or {}).get("body","")
                    await handle_research_reply(subject, body, sender)
                    _processed_uids.add(uid)
                    await h({"method":"tools/call","params":{"name":"mail_mark_seen","arguments":{"uid":uid}}})
            # Admin-Proposal
            elif sender.lower() == "admin@ailinux.me" and not mail.get("seen", True):
                rr = await h({"method":"tools/call","params":{"name":"mail_read","arguments":{"uid":uid}}})
                if rr and not rr.get("error"):
                    body = (rr.get("result") or {}).get("body","")
                    await handle_admin_mail(subject, body)
                    _processed_uids.add(uid)
                    await h({"method":"tools/call","params":{"name":"mail_mark_seen","arguments":{"uid":uid}}})
    except Exception as e:
        logger.error(f"research_loop.check_mail_replies: {e}")

async def research_loop_tick() -> None:
    global _last_scan
    await check_mail_replies()
    if time.time() - _last_scan >= SCAN_INTERVAL:
        await run_daily_scan()
        _last_scan = time.time()
