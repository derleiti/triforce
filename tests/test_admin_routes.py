from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.config import get_settings
from app.services.crawler.user_crawler import user_crawler
from app.services.auto_crawler import auto_crawler

client = TestClient(app)


@pytest.fixture
def restore_settings():
    settings = get_settings()
    snapshot = {
        "user_crawler_workers": settings.user_crawler_workers,
        "user_crawler_max_concurrent": settings.user_crawler_max_concurrent,
        "auto_crawler_enabled": settings.auto_crawler_enabled,
    }
    yield settings
    settings.user_crawler_workers = snapshot["user_crawler_workers"]
    settings.user_crawler_max_concurrent = snapshot["user_crawler_max_concurrent"]
    settings.auto_crawler_enabled = snapshot["auto_crawler_enabled"]


def test_get_crawler_config():
    response = client.get('/v1/admin/crawler/config')
    assert response.status_code == 200
    payload = response.json()
    expected_keys = {
        'user_crawler_workers',
        'user_crawler_max_concurrent',
        'auto_crawler_workers',
        'auto_crawler_enabled',
        'crawler_max_memory_bytes',
        'crawler_flush_interval',
        'crawler_retention_days',
        'wordpress_category_id',
    }
    assert expected_keys.issubset(payload.keys())


def test_update_crawler_config(monkeypatch, restore_settings):
    settings = restore_settings
    original_workers = settings.user_crawler_workers
    original_concurrency = settings.user_crawler_max_concurrent
    original_auto = settings.auto_crawler_enabled

    called = {}

    async def fake_apply_config(*, worker_count=None, max_concurrent=None):
        called['user'] = (worker_count, max_concurrent)
        return {}

    async def fake_start():
        called['auto_start'] = True

    async def fake_stop():
        called['auto_stop'] = True

    monkeypatch.setattr(user_crawler, 'apply_config', fake_apply_config)
    monkeypatch.setattr(auto_crawler, 'start', fake_start)
    monkeypatch.setattr(auto_crawler, 'stop', fake_stop)

    payload = {
        'user_crawler_workers': original_workers + 1,
        'user_crawler_max_concurrent': original_concurrency + 2,
        'auto_crawler_enabled': not original_auto,
    }

    response = client.post('/v1/admin/crawler/config', json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data['updated']['user_crawler_workers'] == original_workers + 1
    assert data['updated']['user_crawler_max_concurrent'] == original_concurrency + 2
    assert data['updated']['auto_crawler_enabled'] == (not original_auto)

    assert called['user'] == (original_workers + 1, original_concurrency + 2)
    if payload['auto_crawler_enabled']:
        assert 'auto_start' in called
    else:
        assert 'auto_stop' in called


def test_control_user_start_idempotent(monkeypatch):
    original_running = getattr(user_crawler, '_running', False)
    user_crawler._running = True

    async def fake_start():
        raise AssertionError('start should not be called when already running')

    monkeypatch.setattr(user_crawler, 'start', fake_start)

    response = client.post('/v1/admin/crawler/control', json={'action': 'start', 'instance': 'user'})
    assert response.status_code == 200
    payload = response.json()
    assert payload['results']['user']['changed'] is False
    assert payload['results']['user']['detail'] == 'already running'

    user_crawler._running = original_running


def test_control_user_stop(monkeypatch):
    original_running = getattr(user_crawler, '_running', False)
    user_crawler._running = True

    async def fake_stop():
        user_crawler._running = False

    monkeypatch.setattr(user_crawler, 'stop', fake_stop)

    response = client.post('/v1/admin/crawler/control', json={'action': 'stop', 'instance': 'user'})
    assert response.status_code == 200
    payload = response.json()
    assert payload['results']['user']['changed'] is True
    assert payload['results']['user']['status'] == 'stopped'

    user_crawler._running = original_running


def test_status_includes_summary_keys():
    response = client.get('/v1/admin/crawler/status')
    assert response.status_code == 200
    payload = response.json()

    assert 'user_crawler' in payload
    assert 'auto_crawler' in payload
    assert 'main_manager' in payload

    user_summary = payload['user_crawler'].get('summary')
    assert user_summary is not None
    for key in ['running', 'workers', 'active_jobs', 'queue_depth', 'last_heartbeat']:
        assert key in user_summary

    manager_summary = payload['main_manager'].get('summary')
    assert manager_summary is not None
    assert 'last_heartbeat' in manager_summary


def test_metrics_include_posts_today():
    response = client.get('/v1/admin/crawler/metrics')
    assert response.status_code == 200
    data = response.json()
    assert 'posts_today' in data
    assert 'posts_today' in data['overview']
