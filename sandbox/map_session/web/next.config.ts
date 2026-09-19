import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The Temporal client uses gRPC and native Node APIs; load it with plain `require` instead of bundling it.
  serverExternalPackages: ["@temporalio/client"],
};

export default nextConfig;
