import { cookies } from 'next/headers';
import { NextRequest } from 'next/server';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

const BRAIN_URL = (
  process.env.BRAIN_INTERNAL_URL ||
  process.env.BRAIN_URL ||
  process.env.NEXT_PUBLIC_BRAIN_URL ||
  'https://dearadeline-withlove-production.up.railway.app'
).replace(/\/$/, '');

const REQUEST_HEADERS = [
  'accept',
  'content-type',
  'last-event-id',
] as const;

const RESPONSE_HEADERS = [
  'cache-control',
  'content-disposition',
  'content-type',
  'etag',
  'last-modified',
] as const;

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const cookieStore = await cookies();
  const studentToken = cookieStore.get('auth_token')?.value;
  const authorization = studentToken
    ? `Bearer ${studentToken}`
    : request.headers.get('authorization');

  const headers = new Headers();
  for (const name of REQUEST_HEADERS) {
    const value = request.headers.get(name);
    if (value) headers.set(name, value);
  }
  if (authorization) headers.set('authorization', authorization);

  const upstreamUrl = new URL(`${BRAIN_URL}/brain/${path.map(encodeURIComponent).join('/')}`);
  request.nextUrl.searchParams.forEach((value, key) => upstreamUrl.searchParams.append(key, value));

  const hasBody = request.method !== 'GET' && request.method !== 'HEAD';
  const upstream = await fetch(upstreamUrl, {
    method: request.method,
    headers,
    body: hasBody ? request.body : undefined,
    cache: 'no-store',
    redirect: 'manual',
    duplex: hasBody ? 'half' : undefined,
  } as RequestInit & { duplex?: 'half' });

  const responseHeaders = new Headers();
  for (const name of RESPONSE_HEADERS) {
    const value = upstream.headers.get(name);
    if (value) responseHeaders.set(name, value);
  }

  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: responseHeaders,
  });
}

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
