import { Track } from "../types";
import { CreditBucket } from "../schemas/standards";

// ── Track → Credit Mapping ────────────────────────────────────────────────────

export interface TrackCreditMapping {
  /** Primary credit bucket this track contributes to */
  primary: CreditBucket;
  /** Secondary bucket (e.g. GOVERNMENT_ECONOMICS also earns PFL) */
  secondary?: CreditBucket;
  /**
   * Name used on the official printed transcript.
   * Never use internal track names like "HOMESTEADING" on an external document.
   */
  externalName: string;
  /**
   * True if this track counts toward the Oklahoma OSRHE 15-unit college-prep core.
   * Used by the OSRHE dashboard in the Transcript UI.
   */
  osrheDashboard?: boolean;
}

/**
 * Maps each of the 10 curriculum tracks to its credit bucket and transcript name.
 * This is the single source of truth for credit attribution — the credit engine
 * imports from here, not from hardcoded conditionals.
 */
export const TRACK_CREDIT_MAP: Record<Track, TrackCreditMapping> = {
  [Track.CREATION_SCIENCE]: {
    primary:        CreditBucket.LAB_SCIENCE,
    secondary:      CreditBucket.ELECTIVE,
    externalName:   "Environmental Science",
    osrheDashboard: true,
  },
  [Track.HEALTH_NATUROPATHY]: {
    primary:      CreditBucket.HEALTH,
    secondary:    CreditBucket.ELECTIVE,
    externalName: "Health Science",
  },
  [Track.HOMESTEADING]: {
    primary:        CreditBucket.LAB_SCIENCE,
    secondary:      CreditBucket.ELECTIVE,
    externalName:   "Agricultural Science & Technology",
    osrheDashboard: true,
  },
  [Track.GOVERNMENT_ECONOMICS]: {
    primary:        CreditBucket.SOCIAL_STUDIES,
    secondary:      CreditBucket.PFL,
    externalName:   "Government & Economics",
    osrheDashboard: true,
  },
  [Track.JUSTICE_CHANGEMAKING]: {
    primary:        CreditBucket.SOCIAL_STUDIES,
    externalName:   "Social Studies & Civics",
    osrheDashboard: true,
  },
  [Track.DISCIPLESHIP]: {
    primary:      CreditBucket.ELECTIVE,
    externalName: "Philosophy & Ethics",
  },
  [Track.TRUTH_HISTORY]: {
    primary:        CreditBucket.SOCIAL_STUDIES,
    externalName:   "American & World History",
    osrheDashboard: true,
  },
  [Track.ENGLISH_LITERATURE]: {
    primary:        CreditBucket.ENGLISH,
    externalName:   "English Language Arts",
    osrheDashboard: true,
  },
  [Track.APPLIED_MATHEMATICS]: {
    primary:        CreditBucket.MATH,
    externalName:   "Applied Mathematics",
    osrheDashboard: true,
  },
  [Track.CREATIVE_ECONOMY]: {
    primary:      CreditBucket.FINE_ARTS,
    secondary:    CreditBucket.ELECTIVE,
    externalName: "Art, Design & Entrepreneurship",
  },
};
