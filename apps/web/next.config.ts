import type { NextConfig } from "next";

// In production the ALB routes /api/* straight to the FastAPI service (same origin,
// so auth cookies and SSE streams need no proxying). Locally there is no ALB, so when
// API_INTERNAL_URL is set at build/dev time we emulate that rule with a rewrite.
const apiInternalUrl = process.env.API_INTERNAL_URL;

const nextConfig: NextConfig = {
  output: "standalone",
  poweredByHeader: false,
  async rewrites() {
    if (!apiInternalUrl) return [];
    return [{ source: "/api/:path*", destination: `${apiInternalUrl}/api/:path*` }];
  },
};

export default nextConfig;
