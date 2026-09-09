import { afterEach, describe, expect, it, vi } from 'vitest';

import { clearAuthCookie, getSessionStatus, setAuthCookie } from '../auth-cookies';

describe('auth cookie client', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('posts the token to the Next session route, not the Brain proxy', async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    await setAuthCookie('parent-jwt');

    expect(fetchMock).toHaveBeenCalledWith('/api/auth-session', expect.objectContaining({
      method: 'POST',
      body: JSON.stringify({ token: 'parent-jwt' }),
      credentials: 'include',
    }));
  });

  it('does not dump the upstream body onto the login page', async () => {
    vi.stubGlobal('fetch', vi.fn(async () =>
      new Response('{"detail":"Invalid token"}', { status: 401 }),
    ));

    await expect(setAuthCookie('bad')).rejects.toThrow(
      'Could not start your family session. Please try signing in again.',
    );
  });

  it('clears the cookie through the same Next session route', async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ ok: true }), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);

    await clearAuthCookie();

    expect(fetchMock).toHaveBeenCalledWith('/api/auth-session', expect.objectContaining({
      method: 'DELETE',
      credentials: 'include',
    }));
  });

  it('reads the session from the Next session route', async () => {
    const fetchMock = vi.fn(async () =>
      new Response(JSON.stringify({ ok: true, user_id: 'parent-1' }), { status: 200 }),
    );
    vi.stubGlobal('fetch', fetchMock);

    await expect(getSessionStatus()).resolves.toBe('parent-1');
    expect(fetchMock).toHaveBeenCalledWith('/api/auth-session', expect.objectContaining({
      method: 'GET',
    }));
  });
});
