import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';

function load(origin) {
  const env = { ...process.env };
  if (origin === undefined) delete env.BACKEND_ORIGIN;
  else env.BACKEND_ORIGIN = origin;
  return spawnSync(process.execPath, ['--input-type=module', '-e',
    `import {config} from './frontend/vercel.ts'; console.log(JSON.stringify(config))`],
    { cwd: new URL('..', import.meta.url), env, encoding: 'utf8' });
}

test('Vercel refuses an absent or unsafe backend origin', () => {
  for (const origin of [undefined, 'http://api.example', 'https://user:pass@api.example',
    'https://api.example/other', 'https://api.example/?token=x', 'https://api.example/#x']) {
    assert.notEqual(load(origin).status, 0);
  }
});

test('Vercel proxies all API paths before the SPA fallback and never caches private responses', () => {
  const result = load('https://api.example/');
  assert.equal(result.status, 0, result.stderr);
  const config = JSON.parse(result.stdout);
  assert.equal(config.framework, 'vite');
  assert.deepEqual(config.rewrites, [
    { source: '/api/:path*', destination: 'https://api.example/api/:path*' },
    { source: '/(.*)', destination: '/index.html' },
  ]);
  const headers = Object.fromEntries(config.headers.find(h => h.source === '/api/:path*').headers.map(h => [h.key, h.value]));
  assert.equal(headers['Cache-Control'], 'no-store');
  assert.equal(headers['CDN-Cache-Control'], 'no-store');
  assert.equal(headers['Vercel-CDN-Cache-Control'], 'no-store');
});
