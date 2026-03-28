import { z } from "zod";
import { Track } from "../enums/tracks";
import { EvidenceSchema } from "./evidence";

export enum BlockType {
  NARRATIVE = "NARRATIVE",               // Story / reading passage
  PRIMARY_SOURCE = "PRIMARY_SOURCE",     // Historical or scientific primary document — evidence required
  QUESTION = "QUESTION",                 // Socratic question prompt
  ACTIVITY = "ACTIVITY",                 // Hands-on or written activity
  SKETCHNOTE = "SKETCHNOTE",             // Visual note-taking prompt
  RESEARCH_MISSION = "RESEARCH_MISSION", // Assigned when ARCHIVE_SILENT fires
  SCRIPTURE = "SCRIPTURE",               // Biblical anchor text
  DEFINITION = "DEFINITION",             // Vocabulary term
}

export enum DifficultyLevel {
  EMERGING = "EMERGING",         // K-2
  DEVELOPING = "DEVELOPING",     // 3-5
  EXPANDING = "EXPANDING",       // 6-8
  MASTERING = "MASTERING",       // 9-12
}

/**
 * Homestead variant allows lesson content to fork based on isHomestead flag.
 */
const HomesteadVariantSchema = z.object({
  enabled: z.boolean(),
  alternateContent: z.string().describe("Land/homestead-adapted version of the block content"),
  practicalApplication: z.string().optional().describe("Hands-on activity specific to homestead context"),
});

export const LessonBlockSchema = z.object({
  id: z.string().uuid(),
  lessonId: z.string().uuid(),
  track: z.nativeEnum(Track),
  blockType: z.nativeEnum(BlockType),
  difficulty: z.nativeEnum(DifficultyLevel),

  title: z.string().min(1),
  content: z.string().describe("Primary lesson content — must be evidence-backed for TRUTH_HISTORY track"),

  homesteadVariant: HomesteadVariantSchema.optional(),
  evidence: z.array(EvidenceSchema).default([]).describe("Sources supporting this block's claims"),

  /**
   * If this block was generated without sufficient evidence,
   * it must NOT be shown to the student. Set via Witness Protocol.
   */
  isSilenced: z.boolean().default(false),

  tags: z.array(z.string()).default([]),
  order: z.number().int().min(0),
  createdAt: z.string().datetime(),
});

export type LessonBlock = z.infer<typeof LessonBlockSchema>;

export const LessonSchema = z.object({
  id: z.string().uuid(),
  title: z.string().min(1),
  tracks: z.array(z.nativeEnum(Track)).min(1),
  blocks: z.array(LessonBlockSchema),
  targetGrades: z.array(z.string()),
  estimatedMinutes: z.number().int().min(5),
  createdAt: z.string().datetime(),
  updatedAt: z.string().datetime(),
});

export type Lesson = z.infer<typeof LessonSchema>;
