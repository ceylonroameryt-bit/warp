import type { NextConfig } from "next";

const isVercel = Boolean(process.env.VERCEL);

const nextConfig: NextConfig = {
  reactStrictMode: true,
  skipTrailingSlashRedirect: true,
  ...(isVercel
    ? {}
    : {
        experimental: {
          cpus: 1,
          workerThreads: false,
        },
      }),
  async redirects() {
    return [
      {
        source: "/contacts",
        destination: "/app/contacts",
        permanent: false,
      },
      {
        source: "/contacts/:path*",
        destination: "/app/contacts/:path*",
        permanent: false,
      },
      {
        source: "/settings/:path*",
        destination: "/app/settings/:path*",
        permanent: false,
      },
    ];
  },
  async rewrites() {
    const apiUrl =
      process.env.INTERNAL_API_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      "http://127.0.0.1:8001";

    return [
      {
        source: "/api/v1/:path*",
        destination: `${apiUrl}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;
