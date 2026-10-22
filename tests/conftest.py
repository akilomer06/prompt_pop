import os
import atexit
import tempfile
from pathlib import Path

ROOT = tempfile.TemporaryDirectory(prefix='promptpop-tests-')
os.environ['DATABASE_URL'] = 'sqlite:///' + str(Path(ROOT.name) / 'test.db').replace('\\', '/')
os.environ['STORAGE_DIR'] = str(Path(ROOT.name) / 'assets')
os.environ['APP_ORIGIN'] = 'http://testserver'
os.environ.pop('EVALUATOR_URL', None)

import pytest
from fastapi.testclient import TestClient
from backend.models import Base, engine, Session, User
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
