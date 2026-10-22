import os
import atexit
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

ROOT = tempfile.TemporaryDirectory(prefix='promptpop-tests-')
test_database = os.getenv('PROMPTPOP_TEST_DATABASE_URL')
if test_database:
    parsed = urlsplit(test_database)
    # The fixture drops its schema. Never accept a live or remote event database.
    if (parsed.scheme not in ('postgresql', 'postgresql+psycopg') or
            parsed.hostname not in ('127.0.0.1', 'localhost') or parsed.path != '/promptpop_test'):
        raise RuntimeError('PostgreSQL tests require a local database named promptpop_test.')
os.environ['DATABASE_URL'] = test_database or 'sqlite:///' + str(Path(ROOT.name) / 'test.db').replace('\\', '/')
os.environ['STORAGE_DIR'] = str(Path(ROOT.name) / 'assets')
os.environ['APP_ORIGIN'] = 'http://testserver'
os.environ['APP_ENV'] = 'development'
os.environ['ASSET_STORAGE'] = 'local'
test_schema = os.getenv('PROMPTPOP_TEST_DATABASE_SCHEMA')
if test_schema:
    if not test_database or test_schema != 'promptpop_test':
        raise RuntimeError('Schema tests require the isolated local PostgreSQL test database.')
    os.environ['DATABASE_SCHEMA'] = test_schema
else: os.environ.pop('DATABASE_SCHEMA', None)
os.environ['COOKIE_SECURE'] = 'false'
for key in ('APP_ORIGINS', 'BOOTSTRAP_ADMIN_PASSWORD', 'BOOTSTRAP_ADMIN_USERNAME'):
    os.environ.pop(key, None)
os.environ.pop('EVALUATOR_URL', None)

import pytest
from fastapi.testclient import TestClient
from backend.models import Base, engine, Session, User
if test_schema:
    from sqlalchemy.schema import CreateSchema
    with engine.begin() as connection: connection.execute(CreateSchema(test_schema, if_not_exists=True))
from backend.seed import initialize
from backend.security import password_hash
from backend.app import app, LIMITS

# Dispose pooled SQLite handles before TemporaryDirectory cleans up on Windows.
atexit.register(engine.dispose)

@pytest.fixture
def env():
    Base.metadata.drop_all(engine)
    initialize()
    LIMITS.clear()
    with Session.begin() as db:
        db.add(User(id='admin', username='admin', password=password_hash('test-admin-pass'), role='admin'))
        db.add(User(id='judge', username='judge', password=password_hash('test-judge-pass'), role='judge'))
    admin = TestClient(app)
    assert admin.post('/api/auth/login', json={'username':'admin','password':'test-admin-pass'}).status_code == 200
    judge = TestClient(app)
    assert judge.post('/api/auth/login', json={'username':'judge','password':'test-judge-pass'}).status_code == 200
    def make_team(name):
        response = admin.post('/api/admin/teams', json={'name':name,'members':[]})
        assert response.status_code == 200, response.text
        credentials = response.json()
        client = TestClient(app)
        assert client.post('/api/auth/login', json={'username':credentials['username'],'password':credentials['access_code']}).status_code == 200
        return client, credentials
    team, a = make_team('Studio North')
    other, b = make_team('Studio South')
    yield dict(admin=admin, judge=judge, team=team, other=other, a=a, b=b, make_team=make_team)
    admin.close(); judge.close(); team.close(); other.close()
