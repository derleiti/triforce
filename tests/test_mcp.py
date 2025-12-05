import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.crawler.user_crawler import user_crawler
from app.services.auto_crawler import auto_crawler
from app.services import chat as chat_service
from app.services.model_registry import registry

client = TestClient(app)


@pytest.fixture
def restore_user_running():
    original = getattr(user_crawler, '_running', False)
    yield
    user_crawler._running = original


def test_mcp_crawl_url(monkeypatch, restore_user_running):
    async def fake_crawl_url(url, keywords=None, max_pages=10, idempotency_key=None):
        class FakeJob:
            allowed_domains = {'example.com'}

            def to_dict(self):
                return {
                    'id': 'job-1',
                    'seeds': [url],
                    'status': 'queued',
                    'priority': 'high',
                    'created_at': '2024-01-01T00:00:00Z',
                }
        return FakeJob()

    monkeypatch.setattr(user_crawler, 'crawl_url', fake_crawl_url)

    payload = {
        'jsonrpc': '2.0',
        'id': '1',
        'method': 'crawl.url',
        'params': {'url': 'https://example.com'},
    }
    response = client.post('/v1/mcp', json=payload)
    assert response.status_code == 200
    result = response.json()['result']
    assert result['job']['id'] == 'job-1'
    assert result['job']['allowed_domains'] == ['example.com']


def test_mcp_llm_invoke(monkeypatch):
    class DummyModel:
        def __init__(self):
            self.id = 'mock-model'
            self.provider = 'mock'
            self.capabilities = ['chat']

    async def fake_get_model(model_id):
        return DummyModel()

    async def fake_stream_chat(model, model_id, messages, stream, temperature=None):
        _ = list(messages)
        yield 'Hello world'

    monkeypatch.setattr(registry, 'get_model', fake_get_model)
    monkeypatch.setattr(chat_service, 'stream_chat', fake_stream_chat)

    payload = {
        'jsonrpc': '2.0',
        'id': 'chat-1',
        'method': 'llm.invoke',
        'params': {
            'model': 'mock-model',
            'messages': [{'role': 'user', 'content': 'Hi there'}],
            'options': {'temperature': 0.1},
        },
    }

    response = client.post('/v1/mcp', json=payload)
    assert response.status_code == 200
    result = response.json()['result']
    assert result['output'] == 'Hello world'
    assert result['usage']['completion_tokens'] >= 1
    assert result['usage']['prompt_tokens'] >= 1


def test_mcp_admin_config_set(monkeypatch):
    updated = {}

    async def fake_apply_config(*, worker_count=None, max_concurrent=None):
        updated['user'] = (worker_count, max_concurrent)
        return {}

    async def fake_start():
        updated['auto'] = 'start'

    async def fake_stop():
        updated['auto'] = 'stop'

    monkeypatch.setattr(user_crawler, 'apply_config', fake_apply_config)
    monkeypatch.setattr(auto_crawler, 'start', fake_start)
    monkeypatch.setattr(auto_crawler, 'stop', fake_stop)

    payload = {
        'jsonrpc': '2.0',
        'id': 'cfg',
        'method': 'admin.crawler.config.set',
        'params': {'user_crawler_workers': 5},
    }

    response = client.post('/v1/mcp', json=payload)
    assert response.status_code == 200
    data = response.json()['result']
    assert data['updated']['user_crawler_workers'] == 5
    assert updated['user'][0] == 5


def test_mcp_status_endpoint():
    response = client.get('/v1/mcp/status')
    assert response.status_code == 200
    data = response.json()
    assert 'status' in data
    assert 'methods' in data