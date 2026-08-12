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
  // Brain requests are handled by app/brain/[...path]/route.ts so the server
  // can attach the secure username/PIN session token before proxying.
};

module.exports = nextConfig;
