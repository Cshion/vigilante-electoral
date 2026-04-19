import type { NextConfig } from "next";

// Parse allowed dev origins from env (comma-separated)
const allowedDevOrigins = process.env.ALLOWED_DEV_ORIGINS
  ? process.env.ALLOWED_DEV_ORIGINS.split(',').map(o => o.trim()).filter(Boolean)
  : [];

const nextConfig: NextConfig = {
  ...(allowedDevOrigins.length > 0 && { allowedDevOrigins }),
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'resultadoelectoral.onpe.gob.pe',
        pathname: '/assets/**',
      },
    ],
  },
};

export default nextConfig;
