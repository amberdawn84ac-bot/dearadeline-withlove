import { z } from "zod";
import { Track } from "../enums/tracks";

export enum GradeLevel {
  K = "K",
  FIRST = "1",
  SECOND = "2",
  THIRD = "3",
  FOURTH = "4",
  FIFTH = "5",
  SIXTH = "6",
  SEVENTH = "7",
  EIGHTH = "8",
  NINTH = "9",
  TENTH = "10",
  ELEVENTH = "11",
  TWELFTH = "12",
}

export enum LearningStyle {
  VISUAL = "VISUAL",
  AUDITORY = "AUDITORY",
  KINESTHETIC = "KINESTHETIC",
  READING_WRITING = "READING_WRITING",
}

export const StudentProfileSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1),
  gradeLevel: z.nativeEnum(GradeLevel),
  learningStyle: z.nativeEnum(LearningStyle).optional(),

  /**
   * Homestead Adaptation Flag
   * When true, all lesson content adapts to include practical,
   * land-based, self-sufficient application examples.
   */
  isHomestead: z.boolean().default(false),

  activeTracks: z.array(z.nativeEnum(Track)).min(1).describe("Curriculum tracks this student is currently enrolled in"),
  completedLessonIds: z.array(z.string().uuid()).default([]),
  researchMissions: z.array(z.string().uuid()).default([]).describe("Pending research missions from ARCHIVE_SILENT pivots"),

  createdAt: z.string().datetime(),
  updatedAt: z.string().datetime(),
});

export type StudentProfile = z.infer<typeof StudentProfileSchema>;
