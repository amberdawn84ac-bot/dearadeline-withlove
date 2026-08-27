const EXPLICIT_LEARNING_REQUEST_RE =
  /\b(i\s+(?:want|would like|need)\s+to\s+(?:learn|understand|know|explore)|teach me|help me (?:learn|understand)|explain|how does|how do|why does|why do|what (?:is|are|causes|caused)|can (?:we|you) (?:learn|study|investigate|explore))\b/i;

const COMPLETED_ACTIVITY_RE =
  /\b(i (?:spent|did|worked|practiced|baked|built|planted|made|helped|cooked|cleaned|drew|painted|sewed|fixed)|today i|this (?:morning|afternoon|week) i|i've been)\b/i;

const COMPLETED_READING_RE =
  /\b(i (?:finished|completed) (?:reading|studying)|i (?:read|studied) (?:a|an|the|my|\d+) (?:book|chapter|lesson|course|novel|poem|play|textbook|worksheet|pages?))\b/i;

/** True when the learner is asking Adeline to begin teaching a subject. */
export function isExplicitLearningRequest(text: string): boolean {
  return EXPLICIT_LEARNING_REQUEST_RE.test(text);
}

/**
 * True only for a report of work already performed. A request to learn always
 * wins over activity recording, even when it includes "I read ..." as context.
 */
export function isCompletedActivityReport(text: string): boolean {
  if (isExplicitLearningRequest(text)) return false;
  return COMPLETED_ACTIVITY_RE.test(text) || COMPLETED_READING_RE.test(text);
}
