import type { NextConfig } from "next";

/**
 * Control UI — Next.js 16.2 Config (isoliert)
 * Basiert auf agent-chat/next.config.ts.
 */
const nextConfig: NextConfig = {
  typedRoutes: true,

  // Docker: standalone output für minimalen Container
  output: "standalone",

  // Performance & Dev
  experimental: {
    turbopackFileSystemCacheForDev: true,
    optimizePackageImports: [
      "lucide-react",
      "motion",
      "@tanstack/react-query",
      "react-pdf",
    ],
    serverComponentsHmrCache: true,
  },

  // Turbopack
  turbopack: {
    rules: {
      "*.md": ["ignore"],
    },
  },

  // Interface & Security
  reactStrictMode: true,
  typescript: {
    ignoreBuildErrors: false,
  },

  // Next.js 16.2: Browser Log Forwarding
  logging: {
    browserToTerminal: true,
  },
};

export default nextConfig;
