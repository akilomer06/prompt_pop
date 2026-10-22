import io
import json
import zipfile
from unittest.mock import patch
import httpx
import pytest
from PIL import Image
from backend.storage import SupabaseStorage, StorageError, AssetMissing
from backend.config import validate_production


@pytest.fixture
def remote(env, monkeypatch):
    objects, calls = {}, []
    secret = 'sb_secret_' + 'test-only-not-a-real-key' * 2
    storage = SupabaseStorage('https://test.supabase.co', secret, 'promptpop-private')

    def provider(request):
        calls.append((request.method, request.url.path))
        assert request.headers['apikey'] == secret
        assert 'authorization' not in request.headers
        path = request.url.path
        if path == '/storage/v1/bucket/promptpop-private':
            return httpx.Response(200, json={'public': False})
        if request.method == 'POST':
            asset_id = path.rsplit('/', 1)[-1]
            assert request.headers['x-upsert'] == 'false'
            objects[asset_id] = request.content
            return httpx.Response(200, json={'Key': asset_id})
        if request.method == 'DELETE':
            for key in json.loads(request.content)['prefixes']: objects.pop(key, None)
            return httpx.Response(200, json=[])
        key = path.rsplit('/', 1)[-1]
        if key not in objects: return httpx.Response(400, json={'statusCode': '404'})
        return httpx.Response(200, content=objects[key], headers={'Content-Type': 'image/png'})

    with httpx.Client(transport=httpx.MockTransport(provider)) as client:
        monkeypatch.setattr('backend.storage.httpx.request', client.request)
        monkeypatch.setattr('backend.app.STORAGE', storage)
        yield storage, objects, calls


def png():
    raw = io.BytesIO()
    Image.new('RGB', (128, 96), 'blue').save(raw, 'PNG')
    return raw.getvalue()


def test_remote_assets_survive_a_new_storage_client_and_remain_private(env, remote):
    storage, objects, calls = remote
    storage.check()
    assert env['admin'].post('/api/admin/control', json={'action': 'start', 'task_id': 1}).status_code == 200
    assert env['admin'].post('/api/admin/control', json={'action': 'end', 'task_id': 1}).status_code == 200
    response = env['admin'].post('/api/admin/tasks/2/reference', files={'image': ('reference.png', png(), 'image/png')})
    assert response.status_code == 200
    reference = response.json()['asset_id']
    before = len(calls)
    assert env['team'].get('/api/assets/' + reference).status_code == 403
    assert len(calls) == before, 'Authorization must happen before private storage access'
    assert env['admin'].post('/api/admin/control', json={'action': 'start', 'task_id': 2}).status_code == 200
    response = env['team'].post('/api/tasks/2/submit', data={'prompt': 'Blue sphere', 'request_key': 'remote-test'},
                               files={'image': ('creation.png', png(), 'image/png')})
    assert response.status_code == 200
    asset_id = response.json()['asset_id']
    fresh = SupabaseStorage('https://test.supabase.co', storage.headers['apikey'], 'promptpop-private')
    assert fresh.read(asset_id) == objects[asset_id]
    assert env['other'].get('/api/assets/' + asset_id).status_code == 403
    received = env['team'].get('/api/assets/' + asset_id)
    assert received.content == objects[asset_id] and received.headers['cache-control'] == 'no-store'
    archive = zipfile.ZipFile(io.BytesIO(env['admin'].get('/api/admin/export-assets').content))
    assert any(name.endswith(asset_id + '.png') for name in archive.namelist())


def test_remote_upload_rollback_removes_uncommitted_objects(env, remote):
    _, objects, _ = remote
    for action in ['start', 'end']:
        env['admin'].post('/api/admin/control', json={'action': action, 'task_id': 1})
    env['admin'].post('/api/admin/tasks/2/reference', files={'image': ('ref.png', png(), 'image/png')})
    env['admin'].post('/api/admin/control', json={'action': 'start', 'task_id': 2})
    before = dict(objects)
    response = env['team'].post('/api/tasks/2/submit', data={'prompt': 'Blue sphere', 'request_key': 'bad-evidence'},
                               files={'image': ('valid.png', png(), 'image/png'), 'evidence': ('invalid.png', b'invalid', 'image/png')})
    assert response.status_code == 422
    assert objects == before
    assert env['team'].get('/api/submissions').json() == []


def test_remote_storage_fails_closed_without_leaking_provider_errors():
    storage = SupabaseStorage('https://test.supabase.co', 'legacy-secret', 'promptpop-private')
    with patch('backend.storage.httpx.request', return_value=httpx.Response(200, json={'public': True})):
        with pytest.raises(StorageError, match='must be private'): storage.check()
    with patch('backend.storage.httpx.request', side_effect=httpx.ConnectError('sensitive provider details')):
        with pytest.raises(StorageError, match='Retry your request') as error: storage.read('image-id')
        assert 'sensitive' not in str(error.value)
    with pytest.raises(StorageError, match='Invalid asset'): storage.read('../another-bucket')


def test_free_production_uses_remote_storage_without_a_render_disk(monkeypatch):
    settings = {'APP_ENV': 'production', 'DATABASE_URL': 'postgresql://u:p@db/event?sslmode=require',
                'APP_ORIGIN': 'https://event.example', 'APP_ORIGINS': '', 'COOKIE_SECURE': 'true',
                'ASSET_STORAGE': 'supabase', 'SUPABASE_URL': 'https://test.supabase.co',
                'SUPABASE_SERVICE_ROLE_KEY': 'sb_secret_' + 'x' * 40, 'SUPABASE_BUCKET': 'promptpop-private', 'RENDER': 'true'}
    for key, value in settings.items(): monkeypatch.setenv(key, value)
    monkeypatch.delenv('PERSISTENT_DATA_DIR', raising=False)
    monkeypatch.delenv('STORAGE_DIR', raising=False)
    validate_production()
    for key, value in [('SUPABASE_URL', 'http://test.supabase.co'), ('SUPABASE_URL', 'https://test.supabase.co/path'),
                       ('SUPABASE_SERVICE_ROLE_KEY', 'sb_publishable_' + 'x' * 40), ('SUPABASE_BUCKET', '../public')]:
        with monkeypatch.context() as changed:
            changed.setenv(key, value)
            with pytest.raises(RuntimeError): validate_production()
