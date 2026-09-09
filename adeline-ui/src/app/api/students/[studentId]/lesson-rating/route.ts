import { NextRequest, NextResponse } from "next/server";
import { resolveBrainBaseUrl } from '@/lib/server/brain-url';

const BRAIN_URL = resolveBrainBaseUrl();

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ studentId: string }> }
) {
  const { studentId } = await params;
  const body = await req.json();
  const token = req.headers.get("authorization") || "";

  const upstream = await fetch(
    `${BRAIN_URL}/students/${studentId}/lesson-rating`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: token },
      body: JSON.stringify(body),
    }
  );

  if (!upstream.ok) {
    return NextResponse.json({ error: "Failed to save rating" }, { status: upstream.status });
  }

  return NextResponse.json({ ok: true });
}
