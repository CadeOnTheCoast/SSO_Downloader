import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    // In production, Vercel handles rewrites via vercel.json to the python serverless function.
    // In development, we proxy to localhost:8000.
    if (process.env.NODE_ENV === 'development') {
      return [
        {
          source: '/api/ssos',
          destination: 'http://127.0.0.1:8000/api/ssos',
        },
        {
          source: '/api/ssos.csv',
          destination: 'http://127.0.0.1:8000/api/ssos.csv',
        },
        {
          source: '/api/options',
          destination: 'http://127.0.0.1:8000/api/options',
        },
        {
          source: '/summary',
          destination: 'http://127.0.0.1:8000/summary',
        },
        {
          source: '/series/:path*',
          destination: 'http://127.0.0.1:8000/series/:path*',
        },
        {
          source: '/records',
          destination: 'http://127.0.0.1:8000/records',
        },
        {
          source: '/filters',
          destination: 'http://127.0.0.1:8000/filters',
        },
        {
          source: '/download',
          destination: 'http://127.0.0.1:8000/download',
        },
      ]
    }
    return []
  },
};

export default nextConfig;
