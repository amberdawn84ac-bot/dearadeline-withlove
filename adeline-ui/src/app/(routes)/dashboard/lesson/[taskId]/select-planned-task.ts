import type { LearningPlanResponse, LessonSuggestion } from '@/lib/brain-client';

export type PlanLookup = {
  suggestions?: LearningPlanResponse['suggestions'];
  family_investigations?: LearningPlanResponse['family_investigations'];
  family_investigation?: LearningPlanResponse['family_investigation'];
  individual_skills?: LearningPlanResponse['individual_skills'];
  roadmap?: LearningPlanResponse['roadmap'] | null;
};

function lanes(plan: PlanLookup): LessonSuggestion[] {
  const seen = new Set<string>();
  const items: LessonSuggestion[] = [];
  for (const item of [
    ...(plan.suggestions ?? []),
    ...(plan.family_investigations ?? []),
    ...(plan.family_investigation ? [plan.family_investigation] : []),
    ...(plan.individual_skills ?? []),
  ]) {
    if (!item?.id || seen.has(item.id)) continue;
    seen.add(item.id);
    items.push(item);
  }
  return items;
}

/**
 * Resolve a Today / Space URL id against the durable plan.
 *
 * Today cards render `family_investigations` first. The Space page used to look
 * only at `suggestions` (and the roadmap), so a family investigation that is
 * on the board but missing from that one array failed with "no longer in the
 * current learning plan" and never even asked the Brain for the saved unit.
 */
export function selectPlannedTask(plan: PlanLookup, requestedId: string): {
  selected: LessonSuggestion | undefined;
  requiredStandardCodes: string[];
} {
  const fromPlan = lanes(plan).find(
    (item) => item.id === requestedId || item.shared_investigation_id === requestedId,
  );
  if (fromPlan) {
    return {
      selected: fromPlan,
      requiredStandardCodes: fromPlan.standard_code ? [fromPlan.standard_code] : [],
    };
  }

  const roadmapDay = plan.roadmap?.months
    ?.flatMap((month) => month.weeks ?? [])
    .flatMap((week) => week.days ?? [])
    .find((day) => day.lesson_id === requestedId);
  if (!roadmapDay) return { selected: undefined, requiredStandardCodes: [] };

  const requiredStandardCodes = roadmapDay.standard_codes ?? [];
  return {
    requiredStandardCodes,
    selected: {
      id: roadmapDay.lesson_id,
      title: roadmapDay.title,
      track: roadmapDay.track,
      description: roadmapDay.description,
      emoji: roadmapDay.emoji,
      priority: 0.5,
      source: 'standard',
      canonical_ready: false,
      mission_kind: 'learning_mission',
      success_criteria: [],
      sequence_policy: roadmapDay.sequence_policy ?? 'SUPPORTED',
      sequence_state: roadmapDay.sequence_state ?? 'BRIDGE_REQUIRED',
      sequence_target_id: requiredStandardCodes[0],
      prerequisite_readiness: 0,
      prerequisite_concept_ids: [],
      prerequisite_standard_ids: roadmapDay.prerequisite_standard_ids ?? [],
      bridge_required: roadmapDay.bridge_required ?? true,
      delivery_mode: 'FAMILY_INVESTIGATION',
      shared_investigation_id: roadmapDay.lesson_id,
      individual_skill_targets: [],
    },
  };
}
