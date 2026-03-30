/**
 * adeline-core/src/schemas/learningActivity.ts
 * ─────────────────────────────────────────────────────────────────
 * xAPI-compatible learning activity records.
 * "Actor [Verb] Object [Result] [Context]"
 *
 * Every lesson block interaction, journal seal, and lab mission
 * generates a LearningActivity. These feed the LRS (Learning Record
 * Store) and drive the RegistrarAgent's transcript generation.
 * ─────────────────────────────────────────────────────────────────
 */
import { z } from "zod";
import { Track } from "../types";

/** xAPI verb vocabulary — based on the ADL xAPI specification */
export enum xAPIVerb {
  EXPERIENCED  = "experienced",   // Viewed or read content
  COMPLETED    = "completed",     // Finished a lesson or block
  ATTEMPTED    = "attempted",     // Started but not finished
  PASSED       = "passed",        // Met mastery threshold
  FAILED       = "failed",        // Did not meet threshold
  SCORED       = "scored",        // Quiz or assessment result
  INTERACTED   = "interacted",    // General interaction
  CREATED      = "created",       // Created an artifact
  SHARED       = "shared",        // Shared work externally
  OBSERVED     = "observed",      // Homestead or lab observation
  PRACTICED    = "practiced",     // Skill practice session
  RESEARCHED   = "researched",    // Research Mission block
  SEALED       = "sealed",        // Journal sealed by RegistrarAgent
}

export const LearningActivitySchema = z.object({
  id:         z.string().uuid(),
  studentId:  z.string().uuid(),

  // xAPI: Verb + Object
  verb:       z.nativeEnum(xAPIVerb),
  objectId:   z.string().describe("lessonId, blockId, or activityId"),
  objectName: z.string().min(1),

  // xAPI: Result
  result: z.object({
    score:      z.number().min(0).max(1).optional().describe("Normalized score 0.0–1.0"),
    durationMs: z.number().int().min(0).optional(),
    completion: z.boolean().optional(),
    response:   z.string().optional().describe("Student's text response or observation"),
  }).optional(),

  // xAPI: Context (Adeline extensions)
  context: z.object({
    track:       z.nativeEnum(Track),
    oasStandard: z.string().optional(),
    gradeLevel:  z.string().optional(),
    isHomestead: z.boolean().optional(),
    agentName:   z.string().optional(),
  }),

  timestamp: z.string().datetime(),
});

export type LearningActivity = z.infer<typeof LearningActivitySchema>;
