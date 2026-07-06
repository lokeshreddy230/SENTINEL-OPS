import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Produce a standalone build for optimized Docker deployment
  output: "standalone",
};

export default nextConfig;
