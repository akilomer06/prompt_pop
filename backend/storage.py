"""Private local or Supabase asset storage. Provider credentials never reach browsers."""
import os
import re
from pathlib import Path
import httpx


class StorageError(RuntimeError): pass
class AssetMissing(StorageError): pass


def object_name(asset_id):
    if not re.fullmatch(r'[a-zA-Z0-9-]{1,64}', asset_id):
        raise StorageError('Invalid asset identifier.')
    return asset_id


class LocalStorage:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def check(self):
        if not self.root.is_dir(): raise StorageError('Private asset directory is unavailable.')

    def write(self, asset_id, content):
        try: (self.root / object_name(asset_id)).write_bytes(content)
        except OSError: raise StorageError('Private image storage is unavailable.') from None

    def read(self, asset_id):
        try: return (self.root / object_name(asset_id)).read_bytes()
        except FileNotFoundError: raise AssetMissing('Asset is unavailable. Contact an organizer.') from None
        except OSError: raise StorageError('Private image storage is unavailable.') from None

    def delete(self, asset_id):
        try: (self.root / object_name(asset_id)).unlink(missing_ok=True)
        except OSError: raise StorageError('Private image cleanup failed.') from None


class SupabaseStorage:
    def __init__(self, url, secret, bucket):
        self.url = url.rstrip('/') + '/storage/v1'
        self.bucket = bucket
        self.headers = {'apikey': secret}
        # Modern secret keys use the gateway's apikey header; legacy service-role keys are JWTs.
        if not secret.startswith('sb_secret_'): self.headers['Authorization'] = 'Bearer ' + secret

    def request(self, method, path, **kwargs):
        try:
            response = httpx.request(method, self.url + path, headers={**self.headers, **kwargs.pop('headers', {})},
                                     timeout=httpx.Timeout(60, connect=10), follow_redirects=False, **kwargs)
            # Storage may return HTTP 400 with statusCode 404 for a missing object.
            if response.status_code >= 400:
                try: code = str(response.json().get('statusCode', response.status_code))
                except (ValueError, AttributeError): code = str(response.status_code)
                if code == '404': raise AssetMissing('Asset is unavailable. Contact an organizer.')
                raise StorageError('Private image storage is unavailable. Retry your request.')
            return response
        except httpx.HTTPError:
            raise StorageError('Private image storage is unavailable. Retry your request.') from None

    def check(self):
        try: bucket = self.request('GET', '/bucket/' + self.bucket).json()
        except (ValueError, AssetMissing): raise StorageError('Create the configured private Supabase bucket before startup.') from None
        if bucket.get('public') is not False:
            raise StorageError('The Supabase upload bucket must be private.')

    def write(self, asset_id, content):
        self.request('POST', '/object/' + self.bucket + '/' + object_name(asset_id), content=content,
                     headers={'Content-Type': 'image/png', 'cache-control': 'no-store', 'x-upsert': 'false'})

    def read(self, asset_id):
        return self.request('GET', '/object/authenticated/' + self.bucket + '/' + object_name(asset_id)).content

    def delete(self, asset_id):
        try: self.request('DELETE', '/object/' + self.bucket, json={'prefixes': [object_name(asset_id)]})
        except AssetMissing: pass


def get_storage():
    mode = os.getenv('ASSET_STORAGE', 'local')
    if mode == 'local': return LocalStorage(os.getenv('STORAGE_DIR', './data/assets'))
    if mode == 'supabase':
        return SupabaseStorage(os.getenv('SUPABASE_URL', ''), os.getenv('SUPABASE_SERVICE_ROLE_KEY', ''),
                               os.getenv('SUPABASE_BUCKET', 'promptpop-private'))
    raise RuntimeError('ASSET_STORAGE must be local or supabase.')
