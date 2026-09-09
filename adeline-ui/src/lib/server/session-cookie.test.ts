import { describe, expect, it } from 'vitest';
import { jwtSubject, sessionCookieDomain, sessionCookieOptions } from './session-cookie';

describe('jwtSubject', () => {
  it('reads sub from a JWT payload', () => {
    const payload = Buffer.from(JSON.stringify({ sub: 'parent-1', email: 'a@b.c' })).toString('base64url');
    expect(jwtSubject(`header.${payload}.sig`)).toBe('parent-1');
  });

  it('returns null for junk', () => {
    expect(jwtSubject('not-a-jwt')).toBeNull();
    expect(jwtSubject('')).toBeNull();
  });
});

describe('sessionCookieDomain', () => {
  it('covers apex and www so the family session survives the redirect', () => {
    expect(sessionCookieDomain({ headers: { get: () => 'www.dearadeline.co' } })).toBe('.dearadeline.co');
    expect(sessionCookieDomain({ headers: { get: () => 'dearadeline.co' } })).toBe('.dearadeline.co');
    expect(sessionCookieDomain({ headers: { get: () => 'localhost:3000' } })).toBeUndefined();
  });

  it('sets Path=/ and Domain on production hosts', () => {
    const options = sessionCookieOptions({ headers: { get: () => 'www.dearadeline.co' } }, 60);
    expect(options.path).toBe('/');
    expect(options.domain).toBe('.dearadeline.co');
    expect(options.httpOnly).toBe(true);
  });
});
