/**
 * The 8-Track Constitution
 * Every lesson, resource, and agent response must be tagged with one or more tracks.
 */
export enum Track {
  CREATION_SCIENCE = "CREATION_SCIENCE",         // 1. God's Creation & Science
  HEALTH_NATUROPATHY = "HEALTH_NATUROPATHY",     // 2. Health / Naturopathy
  HOMESTEADING = "HOMESTEADING",                 // 3. Homesteading & Stewardship
  GOVERNMENT_ECONOMICS = "GOVERNMENT_ECONOMICS", // 4. Government / Economics
  JUSTICE_CHANGEMAKING = "JUSTICE_CHANGEMAKING", // 5. Justice / Change-making
  DISCIPLESHIP = "DISCIPLESHIP",                 // 6. Discipleship & Discernment
  TRUTH_HISTORY = "TRUTH_HISTORY",               // 7. Truth-Based History
  ENGLISH_LITERATURE = "ENGLISH_LITERATURE",     // 8. English Language & Literature
}

export const TRACK_LABELS: Record<Track, string> = {
  [Track.CREATION_SCIENCE]: "God's Creation & Science",
  [Track.HEALTH_NATUROPATHY]: "Health & Naturopathy",
  [Track.HOMESTEADING]: "Homesteading & Stewardship",
  [Track.GOVERNMENT_ECONOMICS]: "Government & Economics",
  [Track.JUSTICE_CHANGEMAKING]: "Justice & Change-making",
  [Track.DISCIPLESHIP]: "Discipleship & Discernment",
  [Track.TRUTH_HISTORY]: "Truth-Based History",
  [Track.ENGLISH_LITERATURE]: "English Language & Literature",
};

export const ALL_TRACKS = Object.values(Track);
