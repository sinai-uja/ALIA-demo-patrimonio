import type { NextConfig } from "next";
import path from "path";
import { loadEnvConfig } from "@next/env";

// Load env vars from config/ instead of project root
const { combinedEnv } = loadEnvConfig(path.join(process.cwd(), "config"));

const allowedDevOrigins = combinedEnv.ALLOWED_DEV_ORIGINS
  ? combinedEnv.ALLOWED_DEV_ORIGINS.split(",")
  : [];

const nextConfig: NextConfig = {
  output: 'standalone',
  ...(allowedDevOrigins.length > 0 && { allowedDevOrigins }),
};

export default nextConfig;
