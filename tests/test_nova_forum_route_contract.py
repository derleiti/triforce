from pathlib import Path

SRC = (Path(__file__).resolve().parents[1] / 'scripts' / 'tools' / 'nova_flarum_bot.py').read_text(encoding='utf-8')


def test_client_chat_endpoint_contract():
    assert 'http://127.0.0.1:9000/v1/chat' in SRC


def test_model_identifier_contract():
    assert 'openrouter/anthropic/claude-sonnet-4' in SRC
    assert 'chat/openrouter/anthropic/claude-sonnet-4' not in SRC


def test_response_text_contract():
    assert 'if "text" in d:' in SRC
    assert 'answer = d["text"].strip()' in SRC
