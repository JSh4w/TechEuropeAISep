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

const apiKey = process.env.NEXT_PUBLIC_FIREBASE_API_KEY || process.env.FIREBASE_API_KEY;
const authDomain = process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN || process.env.FIREBASE_AUTH_DOMAIN;
const projectId = process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || process.env.FIREBASE_PROJECT_ID;
const appId = process.env.NEXT_PUBLIC_FIREBASE_APP_ID || process.env.FIREBASE_APP_ID;
const storageBucket = process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET || process.env.FIREBASE_STORAGE_BUCKET;
const messagingSenderId =
  process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID || process.env.FIREBASE_MESSAGING_SENDER_ID;
const measurementId = process.env.NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID || process.env.FIREBASE_MEASUREMENT_ID;

if (apiKey) process.env.NEXT_PUBLIC_FIREBASE_API_KEY = apiKey;
if (authDomain) process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN = authDomain;
if (projectId) process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID = projectId;
if (appId) process.env.NEXT_PUBLIC_FIREBASE_APP_ID = appId;
if (storageBucket) process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET = storageBucket;
if (messagingSenderId) process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID = messagingSenderId;
if (measurementId) process.env.NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID = measurementId;

const nextConfig: NextConfig = {
  output: "standalone",
  env: {
    ...(apiKey ? { NEXT_PUBLIC_FIREBASE_API_KEY: apiKey } : {}),
    ...(authDomain ? { NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN: authDomain } : {}),
    ...(projectId ? { NEXT_PUBLIC_FIREBASE_PROJECT_ID: projectId } : {}),
    ...(appId ? { NEXT_PUBLIC_FIREBASE_APP_ID: appId } : {}),
    ...(storageBucket ? { NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET: storageBucket } : {}),
    ...(messagingSenderId ? { NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID: messagingSenderId } : {}),
    ...(measurementId ? { NEXT_PUBLIC_FIREBASE_MEASUREMENT_ID: measurementId } : {}),
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
