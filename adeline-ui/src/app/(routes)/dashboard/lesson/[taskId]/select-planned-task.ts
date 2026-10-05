import type { IndividualLesson, LearningPlanResponse, LessonSuggestion } from '@/lib/brain-client';

export type PlanLookup = {
  suggestions?: LearningPlanResponse['suggestions'];
  family_investigations?: LearningPlanResponse['family_investigations'];
  family_investigation?: LearningPlanResponse['family_investigation'];
  individual_skills?: LearningPlanResponse['individual_skills'];
  individual_lessons?: IndividualLesson[];
  progression_checklist?: LearningPlanResponse['progression_checklist'];
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
  if (!roadmapDay) {
    const mini = (plan.individual_lessons ?? []).find(
      (lesson) => lesson.kind === 'gap' && (lesson.investigation_id === requestedId || lesson.id === requestedId),
    );
    if (!mini) return { selected: undefined, requiredStandardCodes: [] };
    const target = mini.skill_target ?? plan.progression_checklist?.find((item) => item.suggestion_id === mini.investigation_id);
    return {
      requiredStandardCodes: target?.standard_code ? [target.standard_code] : [],
      selected: {
        id: mini.investigation_id,
        title: mini.title,
        track: mini.track,
        description: mini.assignment,
        emoji: '✦',
        priority: 1,
        source: 'continue',
        canonical_topic: mini.title,
        canonical_ready: false,
        mission_kind: 'learning_mission',
        success_criteria: [],
        grade_band: target?.working_level,
        concept_id: target?.concept_id,
        standard_code: target?.standard_code,
        sequence_target_id: target?.concept_id ?? target?.standard_code,
        sequence_policy: target ? 'HARD' : 'SUPPORTED',
        sequence_state: target?.sequence_state ?? 'BRIDGE_REQUIRED',
        prerequisite_readiness: 1,
        prerequisite_concept_ids: target?.concept_id ? target.prerequisite_ids ?? [] : [],
        prerequisite_standard_ids: target?.standard_code ? target.prerequisite_ids ?? [] : [],
        bridge_required: !target,
        delivery_mode: 'INDIVIDUAL_SKILL',
        individual_skill_targets: target ? [target] : [],
        learner_progression_targets: target ? [target] : [],
      },
    };
  }

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
