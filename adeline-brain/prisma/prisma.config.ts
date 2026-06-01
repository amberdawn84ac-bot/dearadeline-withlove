import { PrismaClient } from '@prisma/client';

const url = process.env.DATABASE_URL;
const directUrl = process.env.DIRECT_DATABASE_URL;

export const prisma = new PrismaClient({
  datasources: {
    db: {
      url,
    },
  },
});

export const prismaDirect = new PrismaClient({
  datasources: {
    db: {
      url: directUrl,
    },
  },
});

// For Prisma 7 migrations, we need to pass the URL via environment
// The schema.prisma should not have url/directUrl properties
export const prismaMigrate = new PrismaClient({
  datasources: {
    db: {
      url: directUrl || url,
    },
  },
});
