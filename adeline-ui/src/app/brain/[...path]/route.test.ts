import { afterEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';

vi.mock('next/headers', () => ({
  cookies: async () => ({
    get: (name: string) => (name === 'auth_token' ? { value: 'cookie-jwt' } : undefined),
  }),
}));

import { POST } from './route';

describe('Brain proxy request body', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('forwards a buffered JSON body instead of an empty stream', async () => {
    const fetchMock = vi.fn<(input: RequestInfo | URL, init?: RequestInit) => Promise<Response>>(async () =>
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }),
    );
    vi.stubGlobal('fetch', fetchMock);

    const request = new NextRequest('http://localhost/brain/auth/parent/bootstrap', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ name: 'Amber' }),
    });

    const response = await POST(request, { params: Promise.resolve({ path: ['auth', 'parent', 'bootstrap'] }) });
    expect(response.status).toBe(200);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toContain('/brain/auth/parent/bootstrap');
    expect((init as RequestInit & { duplex?: string } | undefined)?.duplex).toBeUndefined();
    const forwarded = init?.body;
    const text = typeof forwarded === 'string'
      ? forwarded
      : forwarded instanceof ArrayBuffer
        ? new TextDecoder().decode(forwarded)
        : forwarded instanceof Uint8Array
          ? new TextDecoder().decode(forwarded)
          : forwarded
            ? await new Response(forwarded as BodyInit).text()
            : '';
    expect(text).toBe(JSON.stringify({ name: 'Amber' }));
  });
});
