import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const config = JSON.parse(readFileSync(new URL('../frontend/vercel.json', import.meta.url), 'utf8'));

test('Vercel targets the assigned HTTPS Render service without credentials', () => {
  const target = new URL(config.rewrites[0].destination);
  assert.equal(target.origin, 'https://prompt-pop-api.onrender.com');
  assert.equal(target.username, '');
  assert.equal(target.password, '');
});

test('Vercel proxies all API paths before the SPA fallback and never caches private responses', () => {
  assert.equal(config.framework, 'vite');
  assert.deepEqual(config.rewrites, [
    { source: '/api/:path*', destination: 'https://prompt-pop-api.onrender.com/api/:path*' },
    { source: '/(.*)', destination: '/index.html' },
  ]);
  const headers = Object.fromEntries(config.headers.find(h => h.source === '/api/:path*').headers.map(h => [h.key, h.value]));
  assert.equal(headers['Cache-Control'], 'no-store');
  assert.equal(headers['CDN-Cache-Control'], 'no-store');
  assert.equal(headers['Vercel-CDN-Cache-Control'], 'no-store');
});
