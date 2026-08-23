/**
 * /api/coppa — COPPA parental verification
 *
 * POST /api/coppa  — generate token, send verification email to parent
 * GET  /api/coppa?token=xxx — parent clicks link, activate account
 *
 * Email sent via Resend (RESEND_API_KEY env var).
 * Token is a 32-byte hex string, expires in 72 hours.
 */

import { NextRequest, NextResponse } from "next/server";
import crypto from "node:crypto";
import { coppaVerificationUrl, sendCoppaVerificationEmail } from '@/lib/server/coppa-email';

const BRAIN_URL = (
  process.env.BRAIN_INTERNAL_URL ||
  process.env.BRAIN_URL ||
  process.env.NEXT_PUBLIC_BRAIN_URL ||
  'http://localhost:8000'
).replace(/\/$/, '');

// ── POST — request parent verification ───────────────────────────────────────
export async function POST(req: NextRequest): Promise<NextResponse> {
  if (!process.env.RESEND_API_KEY) {
    return NextResponse.json({ error: 'Parental verification email is not configured.' }, { status: 503 });
  }
  // Require auth
  const authHeader = req.headers.get("Authorization") ?? "";
  if (!authHeader.startsWith("Bearer ")) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  let body: { studentId: string; studentName: string; parentName: string; parentEmail: string };
  try {
    body = await req.json() as typeof body;
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 });
  }

  const { studentId, studentName, parentName, parentEmail } = body;
  if (!studentId || !studentName || !parentName || !parentEmail) {
    return NextResponse.json({ error: "studentId, studentName, parentName, parentEmail required" }, { status: 422 });
  }

  // Generate token
  const token   = crypto.randomBytes(32).toString("hex");
  const expires = new Date(Date.now() + 72 * 60 * 60 * 1000); // 72 hours

  // Store token in DB via brain API
  try {
    const dbRes = await fetch(`${BRAIN_URL}/api/coppa/token`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: authHeader },
      body: JSON.stringify({ studentId, token, expiresAt: expires.toISOString() }),
    });
    if (!dbRes.ok) {
      const err = await dbRes.text();
      throw new Error(`Brain token store failed: ${err}`);
    }
  } catch (e) {
    console.error("[COPPA POST] token store failed:", e);
    return NextResponse.json({ error: "Failed to generate verification token" }, { status: 502 });
  }

  // Send email
  const verifyUrl = coppaVerificationUrl(token);
  try {
    await sendCoppaVerificationEmail({ parentEmail, parentName, studentName, verifyUrl });
  } catch (e) {
    console.error("[COPPA POST] email failed:", e);
    return NextResponse.json({ error: 'Parental verification email could not be sent.' }, { status: 502 });
  }

  return NextResponse.json({ ok: true, emailSent: true });
}

// ── GET — parent clicks verification link ────────────────────────────────────
export async function GET(req: NextRequest): Promise<NextResponse> {
  const token = req.nextUrl.searchParams.get("token");
  if (!token) {
    return NextResponse.json({ error: "token is required" }, { status: 400 });
  }

  try {
    const res = await fetch(`${BRAIN_URL}/api/coppa/verify`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    });

    if (res.status === 404) {
      return NextResponse.json({ error: "Token not found or already used" }, { status: 404 });
    }
    if (res.status === 410) {
      return NextResponse.json({ error: "Verification link has expired" }, { status: 410 });
    }
    if (!res.ok) {
      throw new Error(`Brain verify failed: ${res.status}`);
    }

    const data = await res.json() as { studentId: string };
    return NextResponse.json({ ok: true, studentId: data.studentId });
  } catch (e) {
    console.error("[COPPA GET] verify failed:", e);
    return NextResponse.json({ error: "Verification failed" }, { status: 502 });
  }
}
