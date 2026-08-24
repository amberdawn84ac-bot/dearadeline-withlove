import { NextRequest, NextResponse } from 'next/server';
import crypto from 'node:crypto';
import { coppaVerificationUrl, sendCoppaVerificationEmail } from '@/lib/server/coppa-email';

const BRAIN_URL = (
  process.env.BRAIN_INTERNAL_URL ||
  process.env.BRAIN_URL ||
  process.env.NEXT_PUBLIC_BRAIN_URL ||
  'https://dearadeline-withlove-production.up.railway.app'
).replace(/\/$/, '');

const COOKIE_NAME = 'auth_token';
const COOKIE_MAX_AGE = 30 * 24 * 60 * 60;

function setSessionCookie(response: NextResponse, token: string) {
  response.cookies.set({
    name: COOKIE_NAME,
    value: token,
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
    maxAge: COOKIE_MAX_AGE,
  });
}

export async function POST(request: NextRequest) {
  const payload = await request.json().catch(() => ({}));
  const mode = payload?.mode === 'register' ? 'register' : payload?.mode === 'login' ? 'login' : null;
  if (!mode) {
    return NextResponse.json({ detail: 'Invalid authentication mode.' }, { status: 400 });
  }

  const requiresParentVerification = mode === 'register' && payload?.age_band === 'UNDER_13';

  // Do not reserve a locked learner account when the consent message cannot
  // be delivered. Parent-created and parent-claimed accounts do not use this
  // self-registration path.
  if (requiresParentVerification && !process.env.RESEND_API_KEY) {
    return NextResponse.json(
      { detail: 'Learner self-registration is temporarily unavailable. A parent can create or connect the learner from the parent dashboard.' },
      { status: 503 },
    );
  }

  const body = { ...payload };
  delete body.mode;
  const consentToken = requiresParentVerification ? crypto.randomBytes(32).toString('hex') : null;
  if (consentToken) body.parent_verification_token = consentToken;

  let upstream: Response;
  try {
    upstream = await fetch(`${BRAIN_URL}/auth/student/${mode}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      cache: 'no-store',
    });
  } catch (error) {
    console.error('[student-auth] Brain auth service unavailable', error);
    return NextResponse.json(
      { detail: 'Account service is temporarily unavailable. Please try again in a moment.' },
      { status: 503 },
    );
  }

  const data = await upstream.json().catch(() => ({ detail: 'Authentication failed.' }));
  if (!upstream.ok) {
    return NextResponse.json(data, { status: upstream.status });
  }

  if (mode === 'register' && data.requires_parent_verification) {
    if (!consentToken) return NextResponse.json({ detail: 'Parental verification could not be started.' }, { status: 502 });
    try {
      await sendCoppaVerificationEmail({
        parentEmail: String(body.parent_email),
        parentName: String(body.parent_name),
        studentName: String(body.display_name),
        verifyUrl: coppaVerificationUrl(consentToken),
      });
    } catch (error) {
      console.error('[student-auth] Parental verification email failed', error);
      return NextResponse.json({ detail: 'The account was reserved, but the parental verification email could not be sent.' }, { status: 502 });
    }
    return NextResponse.json({
      ok: true,
      student_id: data.student_id,
      requires_parent_verification: true,
    });
  }

  if (typeof data?.token !== 'string') {
    return NextResponse.json({ detail: 'Authentication service returned an invalid session.' }, { status: 502 });
  }

  const response = NextResponse.json({
    ok: true,
    student_id: data.student_id,
    user: data.user,
  });
  setSessionCookie(response, data.token);
  return response;
}

export async function GET(request: NextRequest) {
  const token = request.cookies.get(COOKIE_NAME)?.value;
  if (!token) {
    return NextResponse.json({ ok: false }, { status: 401 });
  }

  const authHeaders = { Authorization: `Bearer ${token}` };
  const session = await fetch(`${BRAIN_URL}/brain/auth/session`, {
    headers: authHeaders,
    cache: 'no-store',
  });
  if (!session.ok) {
    const response = NextResponse.json({ ok: false }, { status: 401 });
    response.cookies.delete(COOKIE_NAME);
    return response;
  }

  const sessionData = await session.json();
  const studentId = sessionData?.user_id;
  if (!studentId) {
    return NextResponse.json({ ok: false }, { status: 401 });
  }

  const profileResponse = await fetch(`${BRAIN_URL}/students/${studentId}/profile`, {
    headers: authHeaders,
    cache: 'no-store',
  });
  if (!profileResponse.ok) {
    // A valid parent session is not a student session. Do not clear the shared
    // auth cookie; simply tell student-only consumers that no learner is active.
    return NextResponse.json({ ok: false }, { status: 403 });
  }
  const profile = await profileResponse.json();

  return NextResponse.json({
    ok: true,
    student_id: studentId,
    user: {
      id: studentId,
      name: profile?.name ?? 'Student',
      display_name: profile?.name ?? 'Student',
      gradeLevel: profile?.grade_level ?? '8',
      grade_level: profile?.grade_level ?? '8',
      interests: [],
      learningStyle: null,
      state: null,
      onboardingComplete: true,
      linkCode: profile?.link_code ?? '',
      link_code: profile?.link_code ?? '',
      parentId: profile?.parent_id ?? null,
      parent_id: profile?.parent_id ?? null,
      parentDisplayName: profile?.parent_display_name ?? null,
      parent_display_name: profile?.parent_display_name ?? null,
    },
  });
}

export async function DELETE() {
  const response = NextResponse.json({ ok: true });
  response.cookies.set({
    name: COOKIE_NAME,
    value: '',
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
    maxAge: 0,
  });
  return response;
}
