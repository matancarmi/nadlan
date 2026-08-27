/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    // Proxy /api/* through the frontend's own origin to the backend service.
    // This makes every request same-origin from the browser's point of view,
    // so the session cookie is first-party (not blocked by third-party
    // cookie restrictions in modern browsers) and no CORS is needed.
    const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
    return [{ source: "/api/:path*", destination: `${backendUrl}/api/:path*` }];
  },
};

module.exports = nextConfig;
