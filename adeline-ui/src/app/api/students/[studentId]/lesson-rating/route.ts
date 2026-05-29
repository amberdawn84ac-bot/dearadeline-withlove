import { NextRequest, NextResponse } from "next/server";

const BRAIN_URL = (
  process.env.BRAIN_INTERNAL_URL ||
  process.env.BRAIN_URL ||
  process.env.NEXT_PUBLIC_BRAIN_URL ||
  "https://dearadeline-withlove-production.up.railway.app"
);

export async function POST(
  req: NextRequest,
  { params }: { params: { studentId: string } }
) {
  const { studentId } = params;
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
