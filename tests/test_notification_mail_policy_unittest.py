"""Regression tests for Nova mail reply vs. Suggest-Mode routing."""

from app.mcp.notification_manager import (
    SRC_MAIL,
    _mail_requires_suggestion,
    classify_event,
)


def _event(subject: str, body: str, event_type: str):
    return {
        "source": SRC_MAIL,
        "event_type": event_type,
        "title": f"Mail: {subject}",
        "body": body,
        "metadata": {"subject": subject},
    }


def test_story_mail_is_direct_conversation():
    body = "ich moechte testen ob du direkt antworten kannst. poste einfach eine kurze geschichte."
    event_type = classify_event(SRC_MAIL, "erzaehle mir eine geschichte", body)
    assert event_type == "mail.support"
    assert _mail_requires_suggestion(_event("erzaehle mir eine geschichte", body, event_type)) is False


def test_status_overview_mail_is_direct_conversation():
    body = "Nova, kannst du mir einen Statusueberblick geben? Dies ist auch ein Test des Mail-Notifiers."
    event_type = classify_event(SRC_MAIL, "Uebersicht", body)
    assert event_type == "mail.support"
    assert _mail_requires_suggestion(_event("Uebersicht", body, event_type)) is False


def test_explicit_fix_request_uses_suggest_mode():
    body = "Bitte fix den Fehler im Notifier und optimiere die Logik."
    event_type = classify_event(SRC_MAIL, "Bug", body)
    assert event_type == "mail.action"
    assert _mail_requires_suggestion(_event("Bug", body, event_type)) is True


def test_feature_question_can_be_answered_without_auto_change():
    body = "Ich habe eine Feature-Idee. Was haeltst du davon?"
    event_type = classify_event(SRC_MAIL, "Feature Idee", body)
    assert event_type == "support.feature_req"
    assert _mail_requires_suggestion(_event("Feature Idee", body, event_type)) is False


def test_research_mail_stays_in_suggest_mode():
    body = "Bitte Research zur Notifier-Architektur."
    event_type = classify_event(SRC_MAIL, "Research", body, ["research"])
    assert event_type == "mail.research"
    assert _mail_requires_suggestion(_event("Research", body, event_type)) is True
