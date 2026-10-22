"""Hosting settings shared by local development and the split production deployment."""
import os
from pathlib import Path
from urllib.parse import urlsplit


def database_url(value):
    # Render supplies a standard URL; use the installed psycopg 3 driver.
    for prefix in ('postgres://', 'postgresql://'):
        if value.startswith(prefix):
            return 'postgresql+psycopg://' + value[len(prefix):]
    return value


def allowed_origins():
    return {origin.strip().rstrip('/') for origin in
            [os.getenv('APP_ORIGIN', 'http://localhost:5173'),
             *os.getenv('APP_ORIGINS', '').split(',')] if origin.strip()}


def validate_production():
    if os.getenv('APP_ENV', 'development') != 'production':
        return
    if not database_url(os.getenv('DATABASE_URL', '')).startswith('postgresql+psycopg://'):
        raise RuntimeError('Production requires a PostgreSQL DATABASE_URL.')
    if os.getenv('COOKIE_SECURE', '').lower() != 'true':
        raise RuntimeError('Production requires COOKIE_SECURE=true.')
    if not os.getenv('APP_ORIGIN', '').strip():
        raise RuntimeError('Production requires the exact frontend APP_ORIGIN.')
    for origin in allowed_origins():
        parsed = urlsplit(origin)
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or
                parsed.password or parsed.path or parsed.query or parsed.fragment or '*' in origin):
            raise RuntimeError('Production origins must be exact HTTPS origins without paths or wildcards.')
    data = Path(os.getenv('PERSISTENT_DATA_DIR', ''))
    assets = Path(os.getenv('STORAGE_DIR', ''))
    if (not data.is_absolute() or not assets.is_absolute() or
            not assets.resolve().is_relative_to(data.resolve())):
        raise RuntimeError('Production STORAGE_DIR must be inside an absolute PERSISTENT_DATA_DIR mount.')
    # Fail the health check instead of silently putting event uploads on ephemeral storage.
    if os.getenv('RENDER', '').lower() == 'true' and not os.path.ismount(data):
        raise RuntimeError('The Render persistent data disk is not mounted.')
