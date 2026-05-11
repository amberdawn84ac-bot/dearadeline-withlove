/**
 * logger.ts
 *
 * Environment-aware logger that prevents sensitive debug information
 * from leaking into the production browser console or Vercel logs.
 */

const isProduction = process.env.NODE_ENV === 'production';

export const logger = {
  info: (...args: any[]) => {
    if (!isProduction) {
      console.log(...args);
    }
  },
  warn: (...args: any[]) => {
    if (!isProduction) {
      console.warn(...args);
    }
  },
  error: (...args: any[]) => {
    // We usually want to log errors even in production, but we can sanitize them
    console.error(...args);
  },
  debug: (...args: any[]) => {
    if (!isProduction) {
      console.debug(...args);
    }
  }
};
