import { NextRequest, NextResponse } from 'next/server';
import { resolveBrainBaseUrl } from '@/lib/server/brain-url';

const BRAIN_URL = resolveBrainBaseUrl();

const COOKIE_NAME = 'auth_token';
const COOKIE_MAX_AGE = 7 * 24 * 60 * 60;

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

function clearSessionCookie(response: NextResponse) {
  response.cookies.set({
    name: COOKIE_NAME,
    value: '',
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
    maxAge: 0,
  });
}

function familySessionError(status = 401) {
  return NextResponse.json(
    { detail: 'Could not start your family session. Please try signing in again.' },
    { status },
  );
}

/**
 * Parent/admin sessions used to POST the Supabase JWT through the streaming
 * /brain proxy. That proxy often delivered an empty body (so Brain returned
 * 401/422) and always stripped Set-Cookie, so even a 200 never left an
 * HttpOnly cookie on dearadeline.co. Mirror student-auth: buffer JSON, talk
 * to Railway directly, and set the cookie on this response.
 */
export async function POST(request: NextRequest) {
  const payload = await request.json().catch(() => ({}));
  const token = typeof payload?.token === 'string' ? payload.token.trim() : '';
  if (!token) {
    return NextResponse.json({ detail: 'A sign-in token is required.' }, { status: 400 });
  }

  let upstream: Response;
  try {
    upstream = await fetch(`${BRAIN_URL}/brain/auth/session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token }),
      cache: 'no-store',
    });
  } catch (error) {
    console.error('[auth-session] Brain auth service unavailable', error);
    return NextResponse.json(
      { detail: 'Account service is temporarily unavailable. Please try again in a moment.' },
      { status: 503 },
    );
  }

  const data = await upstream.json().catch(() => ({ detail: 'Authentication failed.' }));
  if (!upstream.ok) {
    return familySessionError(upstream.status === 401 ? 401 : upstream.status);
  }

  const response = NextResponse.json({
    ok: true,
    user_id: data.user_id ?? null,
  });
  setSessionCookie(response, token);
  return response;
}

export async function GET(request: NextRequest) {
  const token = request.cookies.get(COOKIE_NAME)?.value;
  if (!token) {
    return NextResponse.json({ ok: false }, { status: 401 });
  }

  let session: Response;
  try {
    session = await fetch(`${BRAIN_URL}/brain/auth/session`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: 'no-store',
    });
  } catch (error) {
    console.error('[auth-session] Brain session check unavailable', error);
    return NextResponse.json({ ok: false }, { status: 503 });
  }

  if (!session.ok) {
    const response = NextResponse.json({ ok: false }, { status: 401 });
    if (session.status === 401 || session.status === 403) {
      clearSessionCookie(response);
    }
    return response;
  }

  const sessionData = await session.json().catch(() => ({}));
  return NextResponse.json({
    ok: true,
    user_id: sessionData?.user_id ?? null,
  });
}

export async function DELETE() {
  const response = NextResponse.json({ ok: true });
  clearSessionCookie(response);
  return response;
}
