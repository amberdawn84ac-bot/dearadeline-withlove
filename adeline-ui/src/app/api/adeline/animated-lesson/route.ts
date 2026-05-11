import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  const body = await req.json();
  const brainUrl = process.env.NEXT_PUBLIC_BRAIN_URL ?? "https://dearadeline-withlove-production.up.railway.app";

  const upstream = await fetch(`${brainUrl}/lesson/animated`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!upstream.ok) {
    const text = await upstream.text();
    return NextResponse.json(
      { error: "Animated lesson generation failed", detail: text },
      { status: upstream.status }
    );
  }

  return NextResponse.json(await upstream.json());
}
