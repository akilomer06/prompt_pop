"""Check the configured Render backend. No credentials, cookies, or event mutations."""
import json
import os
import time
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *_): return None


def check(url):
    parsed = urlsplit(url)
    if (parsed.scheme != 'https' or not parsed.hostname or
            not parsed.hostname.endswith('.onrender.com') or parsed.username or parsed.password or
            parsed.port not in (None, 443) or parsed.path != '/api/health' or parsed.query or parsed.fragment):
        raise ValueError('RENDER_HEALTH_URL must be the Render HTTPS /api/health endpoint.')
    request = Request(url, headers={'User-Agent': 'PromptPop-HealthCheck/1.0', 'Cache-Control': 'no-cache'})
    for attempt in range(3):
        try:
            with build_opener(NoRedirect).open(request, timeout=90) as response:
                data = json.loads(response.read(65536))
                if response.status == 200 and data.get('status') == 'ok':
                    print('Render backend is healthy.')
                    return
        except (URLError, OSError, ValueError): pass
        if attempt < 2: time.sleep(5)
    raise RuntimeError('Render backend did not pass its readiness check after three attempts.')


if __name__ == '__main__': check(os.environ['RENDER_HEALTH_URL'])
