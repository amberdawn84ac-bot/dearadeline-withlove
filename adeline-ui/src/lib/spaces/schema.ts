import { z } from 'zod';

export const spaceEvaluationSchema = z.object({
  adeline_message: z.string().min(1).describe("Adeline's concise response followed by at most one next question."),
  evaluation: z.enum(['correct', 'partial', 'incorrect', 'not_answered']),
  recommended_action: z.enum(['stay', 'advance', 'complete_unit']),
  is_waiting_for_user: z.boolean(),
  resource_triggers: z.array(z.enum(['show_microscope_diagram', 'display_breakout_tracks'])).max(2),
});

export const spaceTurnRequestSchema = z.object({
  studentId: z.string().min(1),
  planItemId: z.string().min(1),
  userMessage: z.string().trim().min(1).max(4000),
  expectedVersion: z.number().int().nonnegative(),
});

export type SpaceEvaluation = z.infer<typeof spaceEvaluationSchema>;
