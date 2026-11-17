import type { NextConfig } from "next";

// Django (DRF) backend. In production nginx routes /api directly to gunicorn,
// so these rewrites only matter for `next dev` / `next start` without nginx.
const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  // Django URLs end with "/": never let Next add/strip trailing slashes.
  skipTrailingSlashRedirect: true,
  experimental: {
    // Every page is private and rendered in the browser (use(browser()) in
    // providers.tsx), so automatic instant-navigation validation of all pages
    // cannot succeed. Only validate segments that opt in with `instant`.
    instantInsights: { validationLevel: "manual-warning" },
  },
  async rewrites() {
    return [
      { source: "/api/:path*/", destination: `${BACKEND_URL}/api/:path*/` },
      { source: "/api/:path*", destination: `${BACKEND_URL}/api/:path*` },
    ];
  },
};

export default nextConfig;
