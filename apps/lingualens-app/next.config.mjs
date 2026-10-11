// Sent on every response by Next itself, so they apply on Vercel, Cloudflare
// (OpenNext) and `next start` alike.
const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains; preload" },
  // The session recorder needs the microphone; nothing else is used.
  { key: "Permissions-Policy", value: "microphone=(self), camera=(), geolocation=(), payment=()" },
  // Report-only first: violations show in the browser console without
  // blocking, so the policy can be tightened and enforced from evidence.
  {
    key: "Content-Security-Policy-Report-Only",
    value: [
      "default-src 'self'",
      "script-src 'self' 'unsafe-inline'",
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: blob:",
      "media-src 'self' blob: https:",
      "font-src 'self' data:",
      "connect-src 'self' https: http://localhost:* http://127.0.0.1:*",
      "frame-ancestors 'none'",
      "base-uri 'self'",
      "form-action 'self'",
    ].join("; "),
  },
];

/** @type {import('next').NextConfig} */
const nextConfig = {
  devIndicators: false,
  // The e2e Playwright suite drives the app through the 127.0.0.1 loopback
  // host, which Next 16 blocks by default as a "cross-origin" dev resource
  // host. Allow it so dev resources load for e2e runs (localhost stays the
  // default-allowed host).
  allowedDevOrigins: ["127.0.0.1"],
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
};

export default nextConfig;
