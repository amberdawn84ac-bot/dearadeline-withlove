import { generateText, Output } from 'ai';
import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';
import { spaceEvaluationSchema, spaceTurnRequestSchema } from '@/lib/spaces/schema';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

const BRAIN_URL = (process.env.BRAIN_INTERNAL_URL || process.env.BRAIN_URL ||
  process.env.NEXT_PUBLIC_BRAIN_URL || 'https://dearadeline-withlove-production.up.railway.app').replace(/\/$/, '');

function brainHeaders(token: string, internal = false) {
  const headers: Record<string, string> = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
  if (internal && process.env.INTERNAL_API_KEY) headers['X-Internal-Key'] = process.env.INTERNAL_API_KEY;
  return headers;
}

export async function POST(request: Request) {
  const parsed = spaceTurnRequestSchema.safeParse(await request.json().catch(() => null));
  if (!parsed.success) return NextResponse.json({ error: 'Invalid Space message.' }, { status: 400 });
  const token = (await cookies()).get('auth_token')?.value;
  if (!token) return NextResponse.json({ error: 'Your session has ended. Please sign in again.' }, { status: 401 });
  if (!process.env.INTERNAL_API_KEY) {
    return NextResponse.json({ error: 'Space pacing is not configured on this deployment.' }, { status: 503 });
  }

  const { studentId, planItemId, userMessage, expectedVersion } = parsed.data;
  const base = `${BRAIN_URL}/brain/spaces/${encodeURIComponent(studentId)}/${encodeURIComponent(planItemId)}`;
  const stateResponse = await fetch(base, { headers: brainHeaders(token), cache: 'no-store' });
  if (!stateResponse.ok) return NextResponse.json({ error: await stateResponse.text() }, { status: stateResponse.status });
  const state = await stateResponse.json();

  const history = (state.messages as Array<{ role: 'user' | 'assistant'; content: string }>).slice(-12);
  const activityMode = state.status === 'completed'
    ? `This unit's planned activities are already finished — you're in open conversation mode now. The family may ask
follow-up questions, revisit something, or wander into a new question entirely. Answer genuinely and substantively;
there is no "next activity" to advance to, so "recommended_action" should stay "stay" unless the family is clearly
done, in which case "complete_unit" is fine (it is a safe no-op once already complete).

LAST ACTIVITY DISCUSSED: ${state.current_lesson?.title || 'Current lesson'}
${JSON.stringify(state.current_block)}`
    : `The server has selected exactly one current activity. Teach that activity and evaluate only evidence in the learner's newest message.
Never skip ahead. Recommend "advance" only when the learner has supplied the evidence or answer this current activity
explicitly requires. Use "complete_unit" only under that same rule when this is the final activity. Otherwise recommend "stay".

UNIT: ${state.title}
LESSON: ${state.current_lesson?.title || 'Current lesson'}
ACTIVITY ${state.current_block_index + 1} OF ${state.total_blocks}:
${JSON.stringify(state.current_block)}`;

  const { output } = await generateText({
    model: process.env.ADELINE_SPACE_MODEL || 'google/gemini-3.8-flash',
    output: Output.object({ schema: spaceEvaluationSchema }),
    system: `You are Adeline, a warm but rigorous learning companion guiding one family through a unit Space.
Never claim credit, mastery, completion, or standards proficiency directly to the family — that is handled separately
from what you say. Ask no more than one question.
Use display_breakout_tracks only when subject-specific work is useful now, and show_microscope_diagram only when microscopy is relevant.

${activityMode}

RABBIT HOLES: if the family's question or discussion genuinely goes beyond the activity above — a real tangent, not a
passing mention — set "off_plan_topic" to name that concept. Use tier "demonstrated" only when the family's answer
meets the same correctness bar you'd require to advance a planned activity. Use tier "encountered" when a real
question got a real, substantive answer but was not demonstrated to that same correctness bar. Leave "off_plan_topic"
null for every ordinary turn that stayed on the current activity.`,
    messages: [...history, { role: 'user', content: userMessage }],
  });

  const transition = await fetch(`${base}/transition`, {
    method: 'POST', headers: brainHeaders(token, true), cache: 'no-store',
    body: JSON.stringify({ ...output, user_message: userMessage, expected_version: expectedVersion }),
  });
  if (!transition.ok) return NextResponse.json({ error: await transition.text() }, { status: transition.status });
  const nextState = await transition.json();

  let breakoutData = null;
  if (output.resource_triggers.includes('display_breakout_tracks')) {
    const breakout = await fetch(`${base}/breakout-standards`, { headers: brainHeaders(token), cache: 'no-store' });
    if (breakout.ok) breakoutData = await breakout.json();
  }
  return NextResponse.json({ ...nextState, breakout_data: breakoutData });
}
