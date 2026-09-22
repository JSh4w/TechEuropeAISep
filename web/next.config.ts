import type { NextConfig } from "next";
import path from "node:path";
import { fileURLToPath } from "node:url";
import * as nextEnvModule from "@next/env";

interface NextEnvModule {
  loadEnvConfig?: (dir: string, dev?: boolean) => { combinedEnv: Record<string, string | undefined> };
  default?: {
    loadEnvConfig?: (dir: string, dev?: boolean) => { combinedEnv: Record<string, string | undefined> };
  };
}

const envModule = nextEnvModule as unknown as NextEnvModule;
const loadEnvConfig = envModule.loadEnvConfig ?? envModule.default?.loadEnvConfig;
const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
if (typeof loadEnvConfig === "function") {
  loadEnvConfig(projectRoot);
}

const nextConfig: NextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: '/api/backend/:path*',
        destination: process.env.BACKEND_URL || 'http://localhost:8000/:path*',
      },
    ];
  },
};

export default nextConfig;
