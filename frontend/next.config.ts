import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  output: 'standalone',
  
  // Environment variables that are safe to expose to the client
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  },

  // Security headers
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
        ],
      },
    ];
  },

  // Optimize for production
  experimental: {
    optimizePackageImports: ['lucide-react'],
  },

  // TypeScript configuration
  typescript: {
    // Only run type checking in development, not during build
    ignoreBuildErrors: false,
  },

  // ESLint configuration
  eslint: {
    // Only run linting in development, not during build
    ignoreDuringBuilds: false,
  },
};

export default nextConfig;
