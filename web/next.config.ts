import type { NextConfig } from "next";

// Site estático: o motor roda offline em Python e grava public/demo.json; a tela só lê.
const nextConfig: NextConfig = {
  output: "export",
  images: { unoptimized: true },
};

export default nextConfig;
