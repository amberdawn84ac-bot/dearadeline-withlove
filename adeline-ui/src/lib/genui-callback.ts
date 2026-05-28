"use client";

const BRAIN_URL = process.env.NEXT_PUBLIC_BRAIN_URL ?? "";

export interface GenUICallbackResult {
  success: boolean;
  updated_mastery?: number;
  should_re_render?: boolean;
  scaffold_component?: string;
  scaffold_props?: Record<string, unknown>;
}

export async function fireGenUICallback(params: {
  studentId?: string;
  lessonId?: string;
  componentType: string;
  event: string;
  state: Record<string, unknown>;
  blockId?: string;
  track?: string;
}): Promise<GenUICallbackResult | null> {
  if (!params.studentId || !params.lessonId) return null;
  try {
    const res = await fetch(`${BRAIN_URL}/brain/genui/callback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({
        student_id: params.studentId,
        lesson_id: params.lessonId,
        component_type: params.componentType,
        event: params.event,
        state: params.state,
        block_id: params.blockId ?? null,
        track: params.track ?? null,
      }),
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}
