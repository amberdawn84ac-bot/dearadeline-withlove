/**
 * adeline-core/src/schemas/knowledgeGraph.ts
 * ─────────────────────────────────────────────────────────────────
 * 10-Track Knowledge Graph node and edge types (stored in Neo4j).
 *
 * The graph enables multi-hop ZPD reasoning:
 * "How did the Dawes Act (Track 7) change soil health (Track 3)?"
 *
 * PREREQUISITE_OF edges drive ZPD ordering:
 * A student must master concept A before concept B is surfaced.
 * ─────────────────────────────────────────────────────────────────
 */
import { z } from "zod";
import { Track, DifficultyLevel } from "../types";

export const KnowledgeNodeSchema = z.object({
  id:           z.string().uuid(),
  title:        z.string().min(1),
  description:  z.string().min(1),
  track:        z.nativeEnum(Track),
  difficulty:   z.nativeEnum(DifficultyLevel),

  /** OAS standard code, e.g. "OK-SC-7.4" */
  standardCode: z.string().optional(),
  gradeBand:    z.string().optional().describe("'k2', '35', '68', or '912'"),
  tags:         z.array(z.string()).default([]),
  /** True when mastery requires a primary artifact: document, lab record, or student-made product */
  isPrimarySource: z.boolean().default(false),
  createdAt:    z.string().datetime(),
});

export type KnowledgeNode = z.infer<typeof KnowledgeNodeSchema>;

export enum EdgeType {
  PREREQUISITE_OF  = "PREREQUISITE_OF",  // Source must be mastered before target
  BELONGS_TO       = "BELONGS_TO",       // Concept belongs to a Track
  SUPPORTED_BY     = "SUPPORTED_BY",     // Concept supported by an Evidence source
  MAPS_TO_STANDARD = "MAPS_TO_STANDARD", // Concept maps to an OAS standard
  RELATED_TO       = "RELATED_TO",       // Cross-track conceptual connection
}

export const KnowledgeEdgeSchema = z.object({
  id:               z.string().uuid(),
  fromNodeId:       z.string(),
  toNodeId:         z.string(),
  relationshipType: z.nativeEnum(EdgeType),
  /** Strength of the relationship (1.0 = hard prerequisite, 0.3 = loose connection) */
  weight:           z.number().min(0).max(1).default(1.0),
  createdAt:        z.string().datetime(),
});

export type KnowledgeEdge = z.infer<typeof KnowledgeEdgeSchema>;
