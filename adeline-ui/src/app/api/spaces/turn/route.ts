import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';
import { spaceTurnRequestSchema } from '@/lib/spaces/schema';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';
export const maxDuration = 60;

const BRAIN_URL = (process.env.BRAIN_INTERNAL_URL || process.env.BRAIN_URL ||
  process.env.NEXT_PUBLIC_BRAIN_URL || 'https://dearadeline-withlove-production.up.railway.app').replace(/\/$/, '');

// The LLM turn-evaluation itself now happens inside adeline-brain
// (app/api/spaces.py::space_turn), using the same in-house Gemini/Claude/GPT
// factory every other AI call in this app goes through. This route is just a
// thin authenticated proxy -- it no longer calls Vercel's AI Gateway, which
// requires a credit card on file before serving any request and was the one
// thing in this entire app that ever needed one.
export async function POST(request: Request) {
  const parsed = spaceTurnRequestSchema.safeParse(await request.json().catch(() => null));
  if (!parsed.success) return NextResponse.json({ error: 'Invalid Space message.' }, { status: 400 });
  const token = (await cookies()).get('auth_token')?.value;
  if (!token) return NextResponse.json({ error: 'Your session has ended. Please sign in again.' }, { status: 401 });

  const { studentId, planItemId, userMessage, expectedVersion } = parsed.data;
  const response = await fetch(
    `${BRAIN_URL}/brain/spaces/${encodeURIComponent(studentId)}/${encodeURIComponent(planItemId)}/turn`,
    {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      cache: 'no-store',
      body: JSON.stringify({ user_message: userMessage, expected_version: expectedVersion }),
    },
  );
  const result = await response.json().catch(() => null);
  if (!response.ok) {
    return NextResponse.json(
      { error: result?.detail || result?.error || 'Adeline could not continue this Space just now.' },
      { status: response.status },
    );
  }
  return NextResponse.json(result);
}
