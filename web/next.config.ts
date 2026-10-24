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
