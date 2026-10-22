import importlib.util
import io
from pathlib import Path
from unittest.mock import patch
import pytest

spec = importlib.util.spec_from_file_location('health_check', Path(__file__).parents[1] / 'scripts/check-health.py')
health = importlib.util.module_from_spec(spec)
spec.loader.exec_module(health)


@pytest.mark.parametrize('url', ['http://api.onrender.com/api/health', 'https://attacker.example/api/health',
                                'https://api.onrender.com/other', 'https://user:pass@api.onrender.com/api/health',
                                'https://api.onrender.com/api/health?token=secret'])
def test_health_monitor_only_contacts_render_readiness(url):
    with pytest.raises(ValueError): health.check(url)


def test_health_monitor_requires_readiness_json_and_retries_cold_start():
    class Reply(io.BytesIO):
        status = 200
    class Opener:
        count = 0
        def open(self, request, timeout):
            self.count += 1
            return Reply(b'<html>Waking up</html>' if self.count == 1 else b'{"status":"ok"}')
    opener = Opener()
    with patch.object(health, 'build_opener', return_value=opener), patch.object(health.time, 'sleep'):
        health.check('https://api.onrender.com/api/health')
    assert opener.count == 2
