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
    // Vercel production: use NEXT_PUBLIC_BRAIN_URL (Railway backend URL)
    // Docker: use BRAIN_INTERNAL_URL (internal hostname)
    // Local dev: use localhost:8000
    let target =
      process.env.BRAIN_INTERNAL_URL ||
      process.env.BRAIN_URL ||
      process.env.NEXT_PUBLIC_BRAIN_URL;

    if (!target) {
      target = process.env.VERCEL
        ? "https://adeline-brain-production.up.railway.app" // Vercel production fallback
        : "http://localhost:8000"; // Local dev fallback
    }

    // Ensure target doesn't have trailing slash
    const cleanTarget = target.replace(/\/$/, "");

    return [
      {
        source: "/brain/:path*",
        destination: `${cleanTarget}/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
