export const AUTH_COOKIE_NAME = 'auth_token';

type HeaderReader = { headers: { get(name: string): string | null } };

export function sessionCookieDomain(request: HeaderReader): string | undefined {
  const host = (request.headers.get('host') || '').split(':')[0].toLowerCase();
  if (host === 'dearadeline.co' || host === 'www.dearadeline.co' || host.endsWith('.dearadeline.co')) {
    return '.dearadeline.co';
  }
  return undefined;
}

export function sessionCookieOptions(request: HeaderReader, maxAge: number) {
  const domain = sessionCookieDomain(request);
  return {
    name: AUTH_COOKIE_NAME,
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax' as const,
    path: '/',
    maxAge,
    ...(domain ? { domain } : {}),
  };
}

export function jwtSubject(token: string): string | null {
  const parts = token.split('.');
  if (parts.length < 2) return null;
  try {
    const padded = parts[1].replace(/-/g, '+').replace(/_/g, '/').padEnd(Math.ceil(parts[1].length / 4) * 4, '=');
    const payload = JSON.parse(Buffer.from(padded, 'base64').toString('utf8')) as { sub?: unknown };
    return typeof payload.sub === 'string' && payload.sub ? payload.sub : null;
  } catch {
    return null;
  }
}
