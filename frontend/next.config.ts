import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Génère un dossier .next/standalone pour le Dockerfile multi-stage
  output: "standalone",
};

export default nextConfig;
