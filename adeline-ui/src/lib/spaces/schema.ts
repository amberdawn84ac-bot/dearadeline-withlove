import { z } from 'zod';

export const spaceTurnRequestSchema = z.object({
  studentId: z.string().min(1),
  planItemId: z.string().min(1),
  userMessage: z.string().trim().min(1).max(4000),
  expectedVersion: z.number().int().nonnegative(),
});
