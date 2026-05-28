/**
 * Component Registry — metadata for all GenUI adaptive learning components.
 *
 * This registry enables:
 * 1. Backend component selector to pick the right component based on learner state
 * 2. Content tagging and intelligent sequencing
 * 3. Telemetry attribution
 */

export type ComponentCategory =
  | "multimodal"
  | "assessment"
  | "feedback"
  | "visualization"
  | "collaborative";

export type LearnerModality = "visual" | "auditory" | "kinesthetic" | "reading";

export type DifficultyLevel = "SEEDLING" | "GROWING" | "HARVEST";

export interface ComponentMeta {
  id: string;
  displayName: string;
  category: ComponentCategory;
  modalities: LearnerModality[];
  supportedDifficulties: DifficultyLevel[];
  estimatedMinutes: number;
  requiresInteraction: boolean;
  stealthAssessment: boolean;
  description: string;
  tags: string[];
}

export const COMPONENT_REGISTRY: Record<string, ComponentMeta> = {
  // ── Multimodal Representation ─────────────────────────────────────────────
  SimulationEmbed: {
    id: "SimulationEmbed",
    displayName: "Interactive Simulation",
    category: "multimodal",
    modalities: ["visual", "kinesthetic"],
    supportedDifficulties: ["SEEDLING", "GROWING", "HARVEST"],
    estimatedMinutes: 5,
    requiresInteraction: true,
    stealthAssessment: false,
    description: "Embeds PhET, GeoGebra, or Desmos simulations for hands-on exploration",
    tags: ["science", "math", "exploration", "hands-on"],
  },
  VirtualManipulative: {
    id: "VirtualManipulative",
    displayName: "Virtual Manipulative",
    category: "multimodal",
    modalities: ["kinesthetic", "visual"],
    supportedDifficulties: ["SEEDLING", "GROWING"],
    estimatedMinutes: 4,
    requiresInteraction: true,
    stealthAssessment: false,
    description: "Drag-and-drop manipulatives for concrete reasoning (fractions, base-10, etc.)",
    tags: ["math", "concrete", "hands-on", "spatial"],
  },
  VideoExplanation: {
    id: "VideoExplanation",
    displayName: "Video Explanation",
    category: "multimodal",
    modalities: ["visual", "auditory"],
    supportedDifficulties: ["SEEDLING", "GROWING", "HARVEST"],
    estimatedMinutes: 6,
    requiresInteraction: false,
    stealthAssessment: false,
    description: "YouTube/Vimeo embeds or AI-generated narrated slides with chapters",
    tags: ["explanation", "lecture", "visual-learner", "passive"],
  },
  TextExplanation: {
    id: "TextExplanation",
    displayName: "Text Explanation",
    category: "multimodal",
    modalities: ["reading"],
    supportedDifficulties: ["GROWING", "HARVEST"],
    estimatedMinutes: 4,
    requiresInteraction: false,
    stealthAssessment: false,
    description: "Progressive-disclosure text sections with key terms and summary",
    tags: ["reading", "text", "reference", "key-terms"],
  },
  RealWorldApplication: {
    id: "RealWorldApplication",
    displayName: "Real-World Application",
    category: "multimodal",
    modalities: ["reading", "kinesthetic"],
    supportedDifficulties: ["GROWING", "HARVEST"],
    estimatedMinutes: 7,
    requiresInteraction: true,
    stealthAssessment: true,
    description: "Scenario-based problem solving with real-world context",
    tags: ["application", "scenario", "problem-solving", "transfer"],
  },

  // ── Assessment ─────────────────────────────────────────────────────────────
  StealthAssessment: {
    id: "StealthAssessment",
    displayName: "Stealth Assessment",
    category: "assessment",
    modalities: ["reading", "kinesthetic"],
    supportedDifficulties: ["SEEDLING", "GROWING", "HARVEST"],
    estimatedMinutes: 4,
    requiresInteraction: true,
    stealthAssessment: true,
    description: "Disguised-as-interactive-scenario assessment that infers mastery invisibly",
    tags: ["assessment", "stealth", "mastery-inference", "no-test-anxiety"],
  },
  AdaptiveQuiz: {
    id: "AdaptiveQuiz",
    displayName: "Adaptive Quiz",
    category: "assessment",
    modalities: ["reading"],
    supportedDifficulties: ["SEEDLING", "GROWING", "HARVEST"],
    estimatedMinutes: 5,
    requiresInteraction: true,
    stealthAssessment: false,
    description: "Difficulty-adjusting quiz with BKT-driven level changes",
    tags: ["quiz", "adaptive", "mastery-check", "difficulty-scaling"],
  },
  MultiCompetencyWorkspace: {
    id: "MultiCompetencyWorkspace",
    displayName: "Multi-Competency Workspace",
    category: "assessment",
    modalities: ["reading", "kinesthetic"],
    supportedDifficulties: ["GROWING", "HARVEST"],
    estimatedMinutes: 8,
    requiresInteraction: true,
    stealthAssessment: true,
    description: "Multi-task workspace assessing multiple competencies in a single scenario",
    tags: ["multi-skill", "complex", "project-based", "synthesis"],
  },

  // ── Feedback & Scaffolding ─────────────────────────────────────────────────
  CorrectiveOverlay: {
    id: "CorrectiveOverlay",
    displayName: "Corrective Feedback",
    category: "feedback",
    modalities: ["reading", "visual"],
    supportedDifficulties: ["SEEDLING", "GROWING", "HARVEST"],
    estimatedMinutes: 2,
    requiresInteraction: false,
    stealthAssessment: false,
    description: "Detailed error analysis with mistake categorization and better approach",
    tags: ["feedback", "error-correction", "scaffolding", "metacognition"],
  },

  // ── Visualization ──────────────────────────────────────────────────────────
  LearningVelocityCard: {
    id: "LearningVelocityCard",
    displayName: "Learning Velocity",
    category: "visualization",
    modalities: ["visual"],
    supportedDifficulties: ["SEEDLING", "GROWING", "HARVEST"],
    estimatedMinutes: 1,
    requiresInteraction: false,
    stealthAssessment: false,
    description: "Dashboard card showing learning speed, trends, and streaks",
    tags: ["dashboard", "metrics", "motivation", "velocity"],
  },
  ProgressMap: {
    id: "ProgressMap",
    displayName: "Progress Map",
    category: "visualization",
    modalities: ["visual"],
    supportedDifficulties: ["SEEDLING", "GROWING", "HARVEST"],
    estimatedMinutes: 1,
    requiresInteraction: true,
    stealthAssessment: false,
    description: "Node-based map showing learning path progress with mastery indicators",
    tags: ["navigation", "progress", "map", "path"],
  },
  AutoDiagram: {
    id: "AutoDiagram",
    displayName: "Auto-Generated Diagram",
    category: "visualization",
    modalities: ["visual"],
    supportedDifficulties: ["GROWING", "HARVEST"],
    estimatedMinutes: 2,
    requiresInteraction: true,
    stealthAssessment: false,
    description: "AI-generated concept maps, flowcharts, causal chains, and hierarchies",
    tags: ["diagram", "concept-map", "relationships", "structure"],
  },
};

/**
 * Get components by category.
 */
export function getComponentsByCategory(category: ComponentCategory): ComponentMeta[] {
  return Object.values(COMPONENT_REGISTRY).filter((c) => c.category === category);
}

/**
 * Get components supporting a specific modality.
 */
export function getComponentsByModality(modality: LearnerModality): ComponentMeta[] {
  return Object.values(COMPONENT_REGISTRY).filter((c) => c.modalities.includes(modality));
}

/**
 * Get components appropriate for a difficulty level.
 */
export function getComponentsByDifficulty(difficulty: DifficultyLevel): ComponentMeta[] {
  return Object.values(COMPONENT_REGISTRY).filter((c) => c.supportedDifficulties.includes(difficulty));
}

/**
 * Score a component's suitability for a given learner context.
 * Returns 0-1 where 1 is perfect match.
 */
export function scoreComponentFit(
  component: ComponentMeta,
  context: {
    preferredModalities?: LearnerModality[];
    difficulty?: DifficultyLevel;
    timeAvailableMinutes?: number;
    needsAssessment?: boolean;
    tags?: string[];
  }
): number {
  let score = 0.5;

  // Modality match
  if (context.preferredModalities) {
    const overlap = component.modalities.filter((m) => context.preferredModalities!.includes(m));
    score += (overlap.length / Math.max(context.preferredModalities.length, 1)) * 0.2;
  }

  // Difficulty match
  if (context.difficulty && component.supportedDifficulties.includes(context.difficulty)) {
    score += 0.15;
  }

  // Time fit
  if (context.timeAvailableMinutes && component.estimatedMinutes <= context.timeAvailableMinutes) {
    score += 0.1;
  }

  // Assessment need
  if (context.needsAssessment && component.stealthAssessment) {
    score += 0.2;
  }

  // Tag overlap
  if (context.tags) {
    const tagOverlap = component.tags.filter((t) => context.tags!.includes(t));
    score += (tagOverlap.length / Math.max(context.tags.length, 1)) * 0.15;
  }

  return Math.min(1, score);
}
