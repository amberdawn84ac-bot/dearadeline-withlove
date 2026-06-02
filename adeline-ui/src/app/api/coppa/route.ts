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
import { createClient } from "@supabase/supabase-js";
import crypto from "node:crypto";

const BRAIN_URL       = process.env.NEXT_PUBLIC_BRAIN_URL ?? "http://localhost:8000";
const RESEND_API_KEY  = process.env.RESEND_API_KEY ?? "";
const APP_URL         = process.env.NEXT_PUBLIC_APP_URL ?? "https://dearadeline.co";
const FROM_EMAIL      = "Adeline <no-reply@dearadeline.co>";

// ── Supabase admin client (server-side only) ──────────────────────────────────
function getSupabase() {
  const url   = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
  const key   = process.env.SUPABASE_SERVICE_ROLE_KEY ?? "";
  return createClient(url, key, { auth: { persistSession: false } });
}

// ── Send email via Resend ─────────────────────────────────────────────────────
async function sendVerificationEmail(
  parentEmail: string,
  parentName: string,
  studentName: string,
  verifyUrl: string,
): Promise<void> {
  if (!RESEND_API_KEY) {
    console.warn("[COPPA] RESEND_API_KEY not set — skipping email in dev");
    return;
  }

  const html = `
    <div style="font-family: Georgia, serif; max-width: 560px; margin: 0 auto; color: #2F4731;">
      <h2 style="color: #2F4731;">Hello, ${parentName}!</h2>
      <p>
        Your child <strong>${studentName}</strong> has started setting up their
        Dear Adeline account — a Christian homeschool AI learning companion.
      </p>
      <p>
        Because ${studentName} is under 13, we need your verified consent before
        they can begin using the app (required by COPPA).
      </p>
      <p style="margin: 32px 0;">
        <a href="${verifyUrl}"
           style="background:#BD6809;color:#fff;padding:14px 28px;border-radius:8px;
                  text-decoration:none;font-weight:bold;display:inline-block;">
          Approve ${studentName}'s Account
        </a>
      </p>
      <p style="font-size: 13px; color: #666;">
        This link expires in 72 hours. If you did not request this, you can safely ignore
        this email — no account will be activated without your approval.
      </p>
      <hr style="border: 1px solid #E7DAC3; margin: 24px 0;" />
      <p style="font-size: 12px; color: #999;">
        Dear Adeline · Christian Homeschool Learning · dearadeline.co
      </p>
    </div>
  `;

  const res = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${RESEND_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      from:    FROM_EMAIL,
      to:      [parentEmail],
      subject: `Please approve ${studentName}'s Adeline account`,
      html,
    }),
  });

  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Resend error ${res.status}: ${err}`);
  }
}

// ── POST — request parent verification ───────────────────────────────────────
export async function POST(req: NextRequest): Promise<NextResponse> {
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
  const verifyUrl = `${APP_URL}/coppa-verify?token=${token}`;
  try {
    await sendVerificationEmail(parentEmail, parentName, studentName, verifyUrl);
  } catch (e) {
    console.error("[COPPA POST] email failed:", e);
    // Don't fail the request — token is stored; parent can be re-sent
    return NextResponse.json({
      ok: true,
      emailSent: false,
      verifyUrl, // surface for dev/manual use
    });
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
