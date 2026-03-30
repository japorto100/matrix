import type { NextConfig } from "next";

/**
 * Agent Chat UI — Next.js 16.2 Config (isoliert)
 * Basiert auf nextjs-chat/next.config.ts ohne Matrix-spezifische Teile.
 */
const nextConfig: NextConfig = {
  typedRoutes: true,

  // Docker: standalone output für minimalen Container
  output: "standalone",

  // Performance & Dev
  experimental: {
    turbopackFileSystemCacheForDev: true,
    optimizePackageImports: ["lucide-react", "motion", "ai", "@ai-sdk/react"],
    // AI SDK v6 DevTools — gibt Sichtbarkeit in LLM Calls, Token Usage, Agent Flows
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
