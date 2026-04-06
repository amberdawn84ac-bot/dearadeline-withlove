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
    const target =
      process.env.BRAIN_INTERNAL_URL ||
      (process.env.NODE_ENV === "production"
        ? "http://adeline-brain:8000"
        : "http://localhost:8000");

    return [
      {
        source: "/brain/:path*",
        destination: `${target}/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
