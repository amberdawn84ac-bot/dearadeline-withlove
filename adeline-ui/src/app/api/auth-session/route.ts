import { NextRequest, NextResponse } from 'next/server';
import { resolveBrainBaseUrl } from '@/lib/server/brain-url';
import { jwtSubject, AUTH_COOKIE_NAME, sessionCookieOptions } from '@/lib/server/session-cookie';

const BRAIN_URL = resolveBrainBaseUrl();
const COOKIE_MAX_AGE = 7 * 24 * 60 * 60;

function setSessionCookie(response: NextResponse, request: NextRequest, token: string) {
  response.cookies.set({
    ...sessionCookieOptions(request, COOKIE_MAX_AGE),
    value: token,
  });
}

function clearSessionCookie(response: NextResponse, request: NextRequest) {
  response.cookies.set({
    ...sessionCookieOptions(request, 0),
    value: '',
  });
}

function familySessionError(status = 401) {
  return NextResponse.json(
    { detail: 'Could not start your family session. Please try signing in again.' },
    { status },
  );
}

/**
 * Parent/admin sessions. Supabase already issued this JWT; persist it as an
 * HttpOnly cookie on dearadeline.co (www and apex). Brain validation is
 * best-effort — a JWKS miss must not block a parent who already signed in.
 */
export async function POST(request: NextRequest) {
  const payload = await request.json().catch(() => ({}));
  const token = typeof payload?.token === 'string' ? payload.token.trim() : '';
  if (!token) {
    return NextResponse.json({ detail: 'A sign-in token is required.' }, { status: 400 });
  }

  const subject = jwtSubject(token);

  let upstream: Response | null = null;
  try {
    upstream = await fetch(`${BRAIN_URL}/brain/auth/session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token }),
      cache: 'no-store',
    });
  } catch (error) {
    console.error('[auth-session] Brain auth service unavailable', error);
    if (!subject) {
      return NextResponse.json(
        { detail: 'Account service is temporarily unavailable. Please try again in a moment.' },
        { status: 503 },
      );
    }
  }

  if (upstream && upstream.ok) {
    const data = await upstream.json().catch(() => ({ user_id: subject }));
    const response = NextResponse.json({
      ok: true,
      user_id: data.user_id ?? subject,
    });
    setSessionCookie(response, request, token);
    return response;
  }

  if (subject) {
    if (upstream && !upstream.ok) {
      const detail = await upstream.text().catch(() => '');
      console.error('[auth-session] Brain rejected a signed-in parent token', upstream.status, detail);
    }
    const response = NextResponse.json({ ok: true, user_id: subject });
    setSessionCookie(response, request, token);
    return response;
  }

  return familySessionError(upstream?.status === 401 ? 401 : upstream?.status || 401);
}

export async function GET(request: NextRequest) {
  const token = request.cookies.get(AUTH_COOKIE_NAME)?.value;
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
      clearSessionCookie(response, request);
    }
    return response;
  }

  const sessionData = await session.json().catch(() => ({}));
  return NextResponse.json({
    ok: true,
    user_id: sessionData?.user_id ?? null,
  });
}

export async function DELETE(request: NextRequest) {
  const response = NextResponse.json({ ok: true });
  clearSessionCookie(response, request);
  return response;
}
