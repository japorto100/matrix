import type { NextConfig } from "next";

/**
 * Matrix Chat — Next.js 16.2 Config
 * Basiert auf Hauptprojekt-Config ohne cesium/ccxt/trading-spezifische Teile.
 */
const nextConfig: NextConfig = {
  // 1. React Compiler — aktivieren sobald babel-plugin-react-compiler@19-kompatibel
  // reactCompiler: true,
  typedRoutes: true,

  // 2. Unified Caching Model (Next.js 16)
  // cacheComponents: true,

  // 3. Docker: standalone output für minimalen Container
  output: "standalone",

  // 4. Performance & Dev
  experimental: {
    turbopackFileSystemCacheForDev: true,
    optimizePackageImports: ["lucide-react", "framer-motion", "matrix-js-sdk"],
  },

  // 4. Turbopack
  turbopack: {
    rules: {
      "*.md": ["ignore"],
    },
  },

  // 5. Interface & Security
  reactStrictMode: true,
  typescript: {
    ignoreBuildErrors: false,
  },

  // 6. Next.js 16.2: Browser Log Forwarding
  logging: {
    browserToTerminal: true,
  },

  // 7. matrix-js-sdk WASM Support
  // WASM-Dateien für die Rust-Crypto müssen durchgereicht werden
  webpack: (config, { isServer }) => {
    if (!isServer) {
      // WASM für matrix-sdk-crypto-wasm
      config.experiments = {
        ...config.experiments,
        asyncWebAssembly: true,
      };
    }
    return config;
  },
};

export default nextConfig;
