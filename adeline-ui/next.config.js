/** @type {import('next').NextConfig} */
const nextConfig = {
  // "standalone" is for Docker; Vercel uses the default output mode automatically.
  ...(process.env.VERCEL ? {} : { output: "standalone" }),

  /**
   * All adeline-brain calls go through /brain/* on the same origin.
   * Next.js server rewrites to BRAIN_INTERNAL_URL (set in docker-compose or .env).
   * The browser never needs to know the internal hostname.
   *
   * Dev:    BRAIN_INTERNAL_URL=http://localhost:8000
   * Docker: BRAIN_INTERNAL_URL=http://adeline-brain:8000
   */
  async rewrites() {
    // Strictly use environment variable for backend URL
    // Docker: BRAIN_INTERNAL_URL (internal hostname)
    // Vercel production: NEXT_PUBLIC_BRAIN_URL (Railway backend URL)
    // Local dev: localhost:8000
    const backendUrl = (
      process.env.BRAIN_INTERNAL_URL ||
      process.env.BRAIN_URL ||
      process.env.NEXT_PUBLIC_BRAIN_URL ||
      "https://dearadeline-withlove-production.up.railway.app"
    ).replace(/\/$/, "");

    return [
      {
        source: "/brain/:path*",
        destination: `${backendUrl}/brain/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
