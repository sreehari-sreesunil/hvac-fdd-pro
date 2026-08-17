import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Produces a minimal, self-contained server bundle in .next/standalone -
  // only the files actually needed at runtime, not the full node_modules.
  // The current recommended pattern for a Docker deployment, dramatically
  // smaller/faster than copying the whole project + node_modules into
  // the image.
  output: "standalone",
};

export default nextConfig;
