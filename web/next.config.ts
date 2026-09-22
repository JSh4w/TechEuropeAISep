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

const apiKey = process.env.FIREBASE_API_KEY || process.env.NEXT_PUBLIC_FIREBASE_API_KEY;
const authDomain = process.env.FIREBASE_AUTH_DOMAIN || process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN;
const projectId = process.env.FIREBASE_PROJECT_ID || process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID;
const appId = process.env.FIREBASE_APP_ID || process.env.NEXT_PUBLIC_FIREBASE_APP_ID;

if (apiKey) process.env.NEXT_PUBLIC_FIREBASE_API_KEY = apiKey;
if (authDomain) process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN = authDomain;
if (projectId) process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID = projectId;
if (appId) process.env.NEXT_PUBLIC_FIREBASE_APP_ID = appId;

const nextConfig: NextConfig = {
  output: "standalone",
  env: {
    ...(apiKey ? { NEXT_PUBLIC_FIREBASE_API_KEY: apiKey } : {}),
    ...(authDomain ? { NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN: authDomain } : {}),
    ...(projectId ? { NEXT_PUBLIC_FIREBASE_PROJECT_ID: projectId } : {}),
    ...(appId ? { NEXT_PUBLIC_FIREBASE_APP_ID: appId } : {}),
  },
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
