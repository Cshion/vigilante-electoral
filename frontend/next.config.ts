import type { NextConfig } from "next";

const nextConfig: NextConfig = {
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
