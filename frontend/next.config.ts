import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Use static export for serverless GitHub Pages hosting
  output: "export",
  images: {
    unoptimized: true,
  },
  // Set basePath only when building in GitHub Actions CI/CD to match repository subpath
  basePath: process.env.GITHUB_ACTIONS ? "/SENTINEL-OPS" : "",
};

export default nextConfig;
