import { afterEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';

import { DELETE, GET, POST } from './route';

function jsonRequest(method: string, body?: unknown, cookie?: string) {
  const headers = new Headers({ 'content-type': 'application/json' });
  if (cookie) headers.set('cookie', cookie);
  return new NextRequest('http://localhost/api/auth-session', {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

function cookieHeader(response: Response) {
  return response.headers.getSetCookie?.().join('\n') || response.headers.get('set-cookie') || '';
}

describe('POST /api/auth-session', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('buffers the JWT, asks Brain to validate it, and sets an HttpOnly cookie on this host', async () => {
    const fetchMock = vi.fn(async () =>
      new Response(JSON.stringify({ ok: true, user_id: 'parent-1' }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    const response = await POST(jsonRequest('POST', { token: 'parent-jwt' }));
    const payload = await response.json();

    expect(response.status).toBe(200);
    expect(payload).toEqual({ ok: true, user_id: 'parent-1' });
    expect(fetchMock).toHaveBeenCalledWith(
      'https://dearadeline-withlove-production.up.railway.app/brain/auth/session',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ token: 'parent-jwt' }),
      }),
    );
    const cookie = cookieHeader(response);
    expect(cookie).toContain('auth_token=parent-jwt');
    expect(cookie.toLowerCase()).toContain('httponly');
    expect(cookie).toMatch(/Path=\//i);
  });

  it('does not set a cookie when Brain rejects the token', async () => {
    vi.stubGlobal('fetch', vi.fn(async () =>
      new Response(JSON.stringify({ detail: 'Invalid token' }), { status: 401 }),
    ));

    const response = await POST(jsonRequest('POST', { token: 'bad-jwt' }));
    const payload = await response.json();

    expect(response.status).toBe(401);
    expect(payload.detail).toMatch(/family session/i);
    expect(cookieHeader(response)).not.toContain('auth_token=bad-jwt');
  });

  it('rejects a missing token without calling Brain', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);

    const response = await POST(jsonRequest('POST', {}));
    expect(response.status).toBe(400);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('returns 503 when Brain is unreachable', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => {
      throw new Error('ECONNREFUSED');
    }));

    const response = await POST(jsonRequest('POST', { token: 'parent-jwt' }));
    const payload = await response.json();
    expect(response.status).toBe(503);
    expect(payload.detail).toMatch(/temporarily unavailable/i);
  });
});

describe('GET /api/auth-session', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('returns 401 when no cookie is present', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    const response = await GET(jsonRequest('GET'));
    expect(response.status).toBe(401);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('asks Brain to verify the cookie and returns the user id', async () => {
    const fetchMock = vi.fn(async () =>
      new Response(JSON.stringify({ ok: true, user_id: 'parent-1' }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    const response = await GET(jsonRequest('GET', undefined, 'auth_token=parent-jwt'));
    const payload = await response.json();
    expect(response.status).toBe(200);
    expect(payload).toEqual({ ok: true, user_id: 'parent-1' });
    expect(fetchMock).toHaveBeenCalledWith(
      'https://dearadeline-withlove-production.up.railway.app/brain/auth/session',
      expect.objectContaining({
        headers: { Authorization: 'Bearer parent-jwt' },
      }),
    );
  });
});

describe('DELETE /api/auth-session', () => {
  it('clears the host cookie', async () => {
    const response = await DELETE();
    expect(response.status).toBe(200);
    const cookie = cookieHeader(response);
    expect(cookie).toMatch(/auth_token=/);
    expect(cookie).toMatch(/Max-Age=0/i);
  });
});
