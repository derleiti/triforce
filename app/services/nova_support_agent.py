"""
Nova Support Agent v1.0
========================
Spawnt bei Support-Notifys. Auth-Flow, Anti-Phishing, Passwort-Reset.
"""
from __future__ import annotations
import logging, re
from datetime import datetime, timezone
from typing import Optional
logger = logging.getLogger("ailinux.support_agent")

SUPPORT_AGENT_SYSTEM_PROMPT = """\
Du bist Nova, Support-Agent von AILinux (support.ailinux.me).

SPRACHE: Antworte immer in der Sprache des Users.
Wenn nicht Englisch: zusätzlich freundlich darauf hinweisen dass das Forum auf
Englisch ist — aber nie ignorieren, immer helfen.

SUPPORT-FLOW:

A) ALLGEMEINE FRAGEN → direkt beantworten, bei Bedarf auf ailinux.me oder forum.ailinux.me verweisen.

B) USER EINGELOGGT → Profildaten aus Flarum/WP lesen, direkt helfen.

C) ACCOUNT-PROBLEM (nicht eingeloggt / kein Zugang):
   Starte Auth-Flow:

   1. Geheimfrage stellen (max 5 Versuche)
   2. Geburtsdatum abfragen (muss exakt stimmen: TT.MM.JJJJ oder MM/DD/YYYY)
   3. Anschrift abfragen (Straße + Hausnummer ODER Stadt)

   ALLES STIMMT:
   → neue E-Mail-Adresse erfragen
   → E-Mail-Adresse im Profil aktualisieren
   → Passwort-Reset-Mail senden
   → freundlich abschließen → TASK_COMPLETE

   ETWAS STIMMT NICHT (nach allen Versuchen):
   → Account sofort sperren (notify_send mit tag "account_block", priority "high")
   → Warn-Mail an hinterlegte E-Mail via mail_send:
     "Jemand hat versucht auf Ihren Account zuzugreifen. 
      Falls Sie das nicht waren, ist alles sicher.
      Antworten Sie auf diese Mail oder kontaktieren Sie admin@ailinux.me."
   → User höflich mitteilen:
     "Wir konnten Ihre Identität nicht bestätigen.
      Sie erhalten eine E-Mail mit weiteren Schritten.
      Bei Fragen: admin@ailinux.me"
   → Gespräch höflich beenden → TASK_COMPLETE

ANTI-PHISHING:
- Geburtsdatum: KEIN "ungefähr", muss exakt
- Mehr als 5 Versuche bei Geheimfrage = sofort blocken
- Bei offensichtlichem Fishing (widersprüchliche Angaben): sofort blocken

TASK-COMPLETE Signal:
Wenn Aufgabe erledigt: schreibe exakt "TASK_COMPLETE" am Ende.
Der Agent wird dann automatisch beendet.
"""

# ── Spracherkennung ───────────────────────────────────────────────────────────

_LANG = {
    "de": re.compile(r"\b(ich|du|das|die|der|und|ist|nicht|kann|bitte|habe|eine|einem|hilfe|hallo)\b", re.I),
    "fr": re.compile(r"\b(je|tu|le|la|les|et|est|pas|avec|pour|bonjour|merci|aide)\b", re.I),
    "es": re.compile(r"\b(yo|tú|el|la|los|y|es|no|con|para|hola|gracias|ayuda)\b", re.I),
    "it": re.compile(r"\b(io|tu|il|la|e|è|non|con|per|ciao|grazie|aiuto)\b", re.I),
    "pt": re.compile(r"\b(eu|tu|o|a|e|é|não|com|para|olá|obrigado|ajuda)\b", re.I),
    "nl": re.compile(r"\b(ik|je|de|het|en|is|niet|met|voor|hallo|dank|hulp)\b", re.I),
    "ru": re.compile(r"[а-яА-ЯёЁ]{3,}"),
    "ja": re.compile(r"[\u3040-\u309f\u30a0-\u30ff]"),
    "zh": re.compile(r"[\u4e00-\u9fff]"),
    "ar": re.compile(r"[\u0600-\u06ff]"),
}
_FORUM_HINT = {
    "de": "ℹ️ Unser Forum ist auf Englisch ausgerichtet, aber ich helfe dir gerne auf Deutsch!",
    "fr": "ℹ️ Notre forum est principalement en anglais, mais je t'aide volontiers en français!",
    "es": "ℹ️ Nuestro foro es principalmente en inglés, ¡pero con gusto te ayudo en español!",
    "it": "ℹ️ Il nostro forum è principalmente in inglese, ma ti aiuto volentieri in italiano!",
    "pt": "ℹ️ O nosso fórum é principalmente em inglês, mas ajudo-o com prazer em português!",
    "nl": "ℹ️ Ons forum is voornamelijk in het Engels, maar ik help je graag in het Nederlands!",
}
_DEFAULT_HINT = "ℹ️ Our forum is primarily in English, but I'm happy to help you in your language!"

def detect_language(text: str) -> tuple:
    for lang, pat in _LANG.items():
        if pat.search(text):
            return lang, _FORUM_HINT.get(lang, _DEFAULT_HINT)
    return "en", None

def build_support_context(
    forum_post_id=None, forum_user=None, post_content=None,
    notification_body=None,
) -> str:
    lang, hint = detect_language(post_content or notification_body or "")
    parts = [SUPPORT_AGENT_SYSTEM_PROMPT, "\n\n--- SUPPORT-FALL ---\n"]
    if forum_post_id: parts.append(f"Forum-Post ID: {forum_post_id}\n")
    if forum_user: parts.append(f"User: {forum_user}\n")
    if post_content: parts.append(f"Post:\n{post_content[:1000]}\n")
    if notification_body: parts.append(f"Notification:\n{notification_body[:500]}\n")
    if lang != "en": parts.append(f"Erkannte Sprache: {lang} — {hint}\n")
    parts.append("\nAnalysiere den Fall und antworte dem User direkt im Forum oder per E-Mail.")
    return "".join(parts)

# ── Account-Block ─────────────────────────────────────────────────────────────

async def trigger_account_block(username: str, user_email: Optional[str], reason: str = "Failed auth — possible phishing") -> None:
    try:
        from ..mcp.structured_admin import handler as h
        await h({"method":"tools/call","params":{"name":"notify_send","arguments":{
            "title": f"🚨 ACCOUNT BLOCKED: {username}",
            "body": f"Reason: {reason}\nEmail: {user_email or 'unknown'}\nTime: {datetime.now(timezone.utc).isoformat()}\nAction: Manual review + forced password reset before unblock.",
            "source":"system","priority":"high","tags":["account_block","security","phishing"],
        }}})
        if user_email:
            await h({"method":"tools/call","params":{"name":"mail_send","arguments":{
                "to": user_email,
                "subject": "⚠️ Security Alert — Unauthorized access attempt on your AILinux account",
                "body": (
                    "Hello,\n\n"
                    "We detected an unauthorized attempt to access your AILinux account.\n"
                    "As a precaution, your account has been temporarily suspended.\n\n"
                    "If this was you, please reply to this email or contact:\n"
                    "admin@ailinux.me\n\n"
                    "Your account will be re-activated after a mandatory password reset.\n\n"
                    "— Nova Support, AILinux"
                ),
            }}})
        logger.warning(f"support_agent: Account blocked — {username} / {user_email}")
    except Exception as e:
        logger.error(f"support_agent.trigger_account_block: {e}")
