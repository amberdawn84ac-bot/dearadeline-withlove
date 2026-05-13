// Prisma 7 config - relies on env vars being set in shell or .env loaded by Prisma CLI
const databaseUrl = process.env.DIRECT_DATABASE_URL || process.env.DATABASE_URL;

if (!databaseUrl) {
  throw new Error('DIRECT_DATABASE_URL or DATABASE_URL environment variable is required');
}

export default {
  datasources: {
    db: {
      url: databaseUrl,
    },
  },
}
