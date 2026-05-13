import { config } from 'dotenv';
import { resolve } from 'path';

// Load environment variables
config({ path: resolve(__dirname, '..', '.env') });

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
