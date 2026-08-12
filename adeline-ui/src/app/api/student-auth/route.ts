import { NextRequest, NextResponse } from 'next/server';

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

  const body = { ...payload };
  delete body.mode;

  const upstream = await fetch(`${BRAIN_URL}/auth/student/${mode}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    cache: 'no-store',
  });

  const data = await upstream.json().catch(() => ({ detail: 'Authentication failed.' }));
  if (!upstream.ok || typeof data?.token !== 'string') {
    return NextResponse.json(data, { status: upstream.status });
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

  const profileResponse = await fetch(`${BRAIN_URL}/students/${studentId}`, {
    headers: authHeaders,
    cache: 'no-store',
  });
  const profile = profileResponse.ok ? await profileResponse.json() : null;

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
