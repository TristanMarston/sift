import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Let phones on the same wifi load the dev server's scripts (private network addresses, any venue).
  allowedDevOrigins: ["10.*.*.*", "192.168.*.*", "172.*.*.*", "*.local"],
  // Listing photos come from the marketplaces' CDNs; Next resizes them so a 500 KB photo arrives as ~20 KB.
  images: {
    qualities: [70],
    remotePatterns: [
      "media-photos.depop.com",
      "u-mercari-images.mercdn.net",
      "i.ebayimg.com",
      "media-assets.grailed.com",
      "di2ponv0v5otw.cloudfront.net",
    ].map((hostname) => ({ protocol: "https" as const, hostname })),
  },
  // /api/sift/* forwards to the backend, so development (a phone on wifi, the HTTPS dev server) is never blocked
  // by the API's allowed-origins list. Production calls the API directly and only falls back to this route.
  async rewrites() {
    const api = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");
    return api ? [{ source: "/api/sift/:path*", destination: `${api}/:path*` }] : [];
  },
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
