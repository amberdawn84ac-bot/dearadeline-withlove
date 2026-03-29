/**
 * adeline-core/src/schemas/agentResponse.ts
 * ─────────────────────────────────────────────────────────────────
 * Typed responses from the 4 specialist agents in Adeline 2.0.
 * The orchestrator in adeline-brain merges AgentResponses into
 * a final LessonResponse for adeline-ui.
 * ─────────────────────────────────────────────────────────────────
 */
import { z } from "zod";
import { LessonBlockSchema, EvidenceSchema, EvidenceVerdict, Track } from "../types";
import { LearningActivitySchema } from "./learningActivity";
import { TranscriptEntrySchema } from "./transcript";

/**
 * The 4 specialist agents in Adeline 2.0.
 * Each agent handles specific tracks of the 9-Track Constitution.
 *
 *  HISTORIAN    → Tracks 5 (Justice/Change-making) + 7 (Truth-Based History)
 *  SCIENCE      → Tracks 1 (Creation Science) + 3 (Homesteading)
 *  DISCIPLESHIP → Tracks 2 (Health) + 4 (Government) + 6 (Discipleship) + 8 (Literature) + 9 (Applied Math)
 *  REGISTRAR    → All tracks: transcript generation + xAPI statement emission
 */
export enum AgentName {
  HISTORIAN    = "HISTORIAN",
  SCIENCE      = "SCIENCE",
  DISCIPLESHIP = "DISCIPLESHIP",
  REGISTRAR    = "REGISTRAR",
}

/** Maps each Track to its responsible specialist agent */
export const TRACK_AGENT_MAP: Record<string, AgentName> = {
  [Track.CREATION_SCIENCE]:     AgentName.SCIENCE,
  [Track.HEALTH_NATUROPATHY]:   AgentName.DISCIPLESHIP,
  [Track.HOMESTEADING]:         AgentName.SCIENCE,
  [Track.GOVERNMENT_ECONOMICS]: AgentName.DISCIPLESHIP,
  [Track.JUSTICE_CHANGEMAKING]: AgentName.HISTORIAN,
  [Track.DISCIPLESHIP]:         AgentName.DISCIPLESHIP,
  [Track.TRUTH_HISTORY]:        AgentName.HISTORIAN,
  [Track.ENGLISH_LITERATURE]:   AgentName.DISCIPLESHIP,
  [Track.APPLIED_MATHEMATICS]:  AgentName.DISCIPLESHIP,
};

export const AgentResponseSchema = z.object({
  agentName:    z.nativeEnum(AgentName),
  lessonBlocks: z.array(LessonBlockSchema),

  /** Overall Witness Protocol verdict for this agent's output batch */
  truthVerdict: z.nativeEnum(EvidenceVerdict),
  citations:    z.array(EvidenceSchema).default([]),

  metadata: z.object({
    processingMs:    z.number().int().optional(),
    modelUsed:       z.string().optional(),
    retrievedChunks: z.number().int().optional(),
    witnessPassed:   z.boolean(),
  }),

  /** RegistrarAgent only — xAPI statements emitted for this lesson */
  xapiStatements: z.array(LearningActivitySchema).default([]),
  /** RegistrarAgent only — CASE-compatible credits awarded */
  creditsAwarded: z.array(TranscriptEntrySchema).default([]),
});

export type AgentResponse = z.infer<typeof AgentResponseSchema>;
