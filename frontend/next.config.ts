import type { NextConfig } from "next";
import path from "path";
import { loadEnvConfig } from "@next/env";

// Load env vars from config/ instead of project root
const { combinedEnv } = loadEnvConfig(path.join(process.cwd(), "config"));

const nextConfig: NextConfig = {
  output: 'standalone',
  env: {
    NEXT_PUBLIC_API_URL: combinedEnv.NEXT_PUBLIC_API_URL ?? "http://localhost:18080/api/v1",
  },
};

export default nextConfig;
