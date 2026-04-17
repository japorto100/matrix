import type { NextConfig } from "next";

/**
 * frontend_merger — Next.js 16.2 Config
 *
 * Mountet Matrix Chat, Agent Chat und Control UI unter einer App.
 * Vereint die Konfigurationen der drei Quellen:
 *   - nextjs-chat (Matrix, braucht WASM fuer matrix-sdk-crypto-wasm)
 *   - agent-chat (AI SDK DevTools, MCP)
 *   - control-ui (Query-Heavy, react-pdf)
 */
const nextConfig: NextConfig = {
	typedRoutes: true,

	// Standalone build fuer podman/docker Container
	output: "standalone",

	experimental: {
		turbopackFileSystemCacheForDev: true,
		serverComponentsHmrCache: true,
		optimizePackageImports: [
			"lucide-react",
			"motion",
			"ai",
			"@ai-sdk/react",
			"matrix-js-sdk",
			"@tanstack/react-query",
			"react-pdf",
		],
	},

	turbopack: {
		rules: {
			"*.md": ["ignore"],
		},
	},

	reactStrictMode: true,
	typescript: {
		ignoreBuildErrors: false,
	},

	logging: {
		browserToTerminal: true,
	},

	// matrix-js-sdk Rust-Crypto braucht asyncWebAssembly im Client-Bundle.
	webpack: (config, { isServer }) => {
		if (!isServer) {
			config.experiments = {
				...config.experiments,
				asyncWebAssembly: true,
			};
		}
		return config;
	},
};

export default nextConfig;
