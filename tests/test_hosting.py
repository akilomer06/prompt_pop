from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from sqlalchemy.exc import OperationalError
from backend.app import app
from backend.bootstrap import bootstrap_admin
from backend.config import database_url, validate_production
from backend.models import Session, User, Audit
from backend.security import verify_password


@pytest.mark.parametrize('prefix', ['postgres://', 'postgresql://', 'postgresql+psycopg://'])
def test_render_connection_string_uses_installed_driver(prefix):
    assert database_url(prefix + 'user:encoded%40pass@db:5432/event') == 'postgresql+psycopg://user:encoded%40pass@db:5432/event'
    assert database_url('sqlite:///event.db') == 'sqlite:///event.db'


def test_proxy_requests_and_origin_rejection(env, monkeypatch):
    # No lifespan here: this test deliberately keeps the isolated SQLite test DB.
    monkeypatch.setenv('APP_ENV', 'production')
    monkeypatch.setenv('APP_ORIGIN', 'https://promptpop.example')
    monkeypatch.setenv('APP_ORIGINS', 'https://preview.example')
    monkeypatch.setenv('COOKIE_SECURE', 'true')
    client = TestClient(app, base_url='https://backend.example')
    credentials = {'username': 'admin', 'password': 'test-admin-pass'}
    for origin in ['https://promptpop.example', 'https://preview.example']:
        response = client.post('/api/auth/login', json=credentials, headers={'Origin': origin, 'Sec-Fetch-Site': 'same-origin'})
        assert response.status_code == 200
        cookie = response.headers['set-cookie']
        assert all(flag in cookie for flag in ['Secure', 'HttpOnly', 'SameSite=strict', 'Path=/'])
        assert 'Domain=' not in cookie
        assert client.get('/api/me').status_code == 200
        for key in ['cache-control', 'cdn-cache-control', 'vercel-cdn-cache-control']:
            assert response.headers[key] == 'no-store'
    for origin in ['https://attacker.example', 'https://other.vercel.app', 'https://backend.example']:
        assert client.post('/api/auth/login', json=credentials, headers={'Origin': origin}).status_code == 403
    assert client.post('/api/auth/login', json=credentials, headers={'Origin': 'https://promptpop.example', 'Sec-Fetch-Site': 'cross-site'}).status_code == 403
    assert client.get('/api/nonexistent').status_code == 404
    assert client.post('/api/auth/logout', headers={'Origin': 'https://promptpop.example'}).status_code == 200
    assert client.get('/api/me').status_code == 401
    client.close()


def test_readiness_reports_database_failure(env):
    with patch('backend.app.Session', side_effect=OperationalError('SELECT 1', {}, Exception('private database details'))):
        response = env['admin'].get('/api/health')
    assert response.status_code == 503
    assert response.json() == {'detail': 'Database is unavailable.'}
    assert env['admin'].get('/api/health').status_code == 200


def test_production_requires_durable_secure_configuration(monkeypatch, tmp_path):
    settings = {'APP_ENV': 'production', 'DATABASE_URL': 'postgres://u:p@db/event',
                'APP_ORIGIN': 'https://promptpop.example', 'COOKIE_SECURE': 'true',
                'PERSISTENT_DATA_DIR': str(tmp_path), 'STORAGE_DIR': str(tmp_path / 'assets')}
    monkeypatch.delenv('RENDER', raising=False)
    monkeypatch.delenv('APP_ORIGINS', raising=False)
    for key, value in settings.items(): monkeypatch.setenv(key, value)
    validate_production()
    for key, value in [('DATABASE_URL', 'sqlite:///ephemeral.db'), ('COOKIE_SECURE', 'false'),
                       ('APP_ORIGIN', ''), ('APP_ORIGIN', 'http://insecure.example'),
                       ('APP_ORIGIN', 'https://*.vercel.app'), ('APP_ORIGIN', 'https://example.org/path'),
                       ('APP_ORIGINS', 'https://user:password@example.org'),
                       ('STORAGE_DIR', str(tmp_path.parent / 'ephemeral'))]:
        with monkeypatch.context() as changed:
            changed.setenv(key, value)
            with pytest.raises(RuntimeError): validate_production()
    monkeypatch.setenv('RENDER', 'true')
    with patch('backend.config.os.path.ismount', return_value=False):
        with pytest.raises(RuntimeError, match='not mounted'): validate_production()
    with patch('backend.config.os.path.ismount', return_value=True): validate_production()


def test_first_organizer_bootstrap_never_resets_password(env, monkeypatch):
    with Session.begin() as db:
        for user in db.scalars(select(User).where(User.role == 'admin')): user.role = 'judge'
    monkeypatch.setenv('BOOTSTRAP_ADMIN_USERNAME', 'Organizer')
    monkeypatch.setenv('BOOTSTRAP_ADMIN_PASSWORD', 'a-long-generated-secret')
    bootstrap_admin()
    monkeypatch.setenv('BOOTSTRAP_ADMIN_PASSWORD', 'a-different-secret-on-redeploy')
    bootstrap_admin()
    with Session() as db:
        user = db.scalar(select(User).where(User.role == 'admin'))
        assert user.username == 'organizer'
        assert verify_password('a-long-generated-secret', user.password)
        assert not verify_password('a-different-secret-on-redeploy', user.password)
        assert db.scalar(select(func.count()).select_from(User).where(User.role == 'admin')) == 1
        logs = db.scalars(select(Audit).where(Audit.action == 'admin_bootstrapped')).all()
        assert len(logs) == 1
        assert logs[0].details == {'username': 'organizer'}


def test_first_production_bootstrap_requires_strong_private_secret(env, monkeypatch):
    with Session.begin() as db:
        for user in db.scalars(select(User).where(User.role == 'admin')): user.role = 'judge'
    monkeypatch.setenv('APP_ENV', 'production')
    with pytest.raises(RuntimeError, match='BOOTSTRAP_ADMIN_PASSWORD'): bootstrap_admin()
    monkeypatch.setenv('BOOTSTRAP_ADMIN_PASSWORD', 'short')
    with pytest.raises(RuntimeError, match='16–200'): bootstrap_admin()
