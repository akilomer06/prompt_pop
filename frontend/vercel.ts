// BACKEND_ORIGIN is a Vercel build setting, never a browser-exposed VITE_ secret.
// No runtime configuration dependency is needed to export this object.
const origin = process.env.BACKEND_ORIGIN;
if (!origin) throw new Error('Set BACKEND_ORIGIN to the Render service HTTPS origin before deploying.');
const parsed = new URL(origin);
if (parsed.protocol !== 'https:' || parsed.username || parsed.password ||
    parsed.pathname !== '/' || parsed.search || parsed.hash) {
  throw new Error('BACKEND_ORIGIN must be an HTTPS origin without credentials, path, query, or fragment.');
}

export const config = {
  framework: 'vite',
  installCommand: 'npm ci',
  buildCommand: 'npm run build',
  outputDirectory: 'dist',
  headers: [
    {
      source: '/(.*)',
      headers: [
        { key: 'X-Content-Type-Options', value: 'nosniff' },
        { key: 'X-Frame-Options', value: 'DENY' },
        { key: 'Referrer-Policy', value: 'same-origin' },
        { key: 'Strict-Transport-Security', value: 'max-age=31536000' },
        { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
        { key: 'Content-Security-Policy', value: "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' blob: data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'" },
      ],
    },
    {
      source: '/api/:path*',
      headers: [
        { key: 'Cache-Control', value: 'no-store' },
        { key: 'CDN-Cache-Control', value: 'no-store' },
        { key: 'Vercel-CDN-Cache-Control', value: 'no-store' },
      ],
    },
  ],
  rewrites: [
    { source: '/api/:path*', destination: `${parsed.origin}/api/:path*` },
    { source: '/(.*)', destination: '/index.html' },
  ],
};
