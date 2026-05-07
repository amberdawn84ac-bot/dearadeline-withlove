/**
 * Cookie-based authentication utilities for production-grade security.
 * 
 * These functions manage HttpOnly, Secure, SameSite cookies containing
 * Supabase JWT tokens. This eliminates localStorage-based token storage
 * which is vulnerable to XSS attacks.
 * 
 * Cookie properties (set by backend):
 * - HttpOnly: Prevents JavaScript access (XSS protection)
 * - Secure: HTTPS only
 * - SameSite=Lax: CSRF protection while allowing top-level navigation
 * - Path=/brain: Only sent to backend API routes
 * - Max-Age=7 days
 */

const AUTH_COOKIE_ENDPOINT = '/brain/auth/session'

/**
 * Set auth cookie after successful Supabase login/signup.
 * 
 * @param token - Supabase JWT access token
 * @throws Error if cookie cannot be set
 */
export async function setAuthCookie(token: string): Promise<void> {
  const response = await fetch(AUTH_COOKIE_ENDPOINT, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ token }),
    credentials: 'include', // Important: sends/receives cookies
  })

  if (!response.ok) {
    const error = await response.text()
    throw new Error(`Failed to set auth cookie: ${error}`)
  }
}

/**
 * Clear auth cookie on logout.
 */
export async function clearAuthCookie(): Promise<void> {
  await fetch(AUTH_COOKIE_ENDPOINT, {
    method: 'DELETE',
    credentials: 'include',
  })
}

/**
 * Check if user has valid session (via cookie).
 * 
 * @returns User ID if authenticated, null otherwise
 */
export async function getSessionStatus(): Promise<string | null> {
  try {
    const response = await fetch(AUTH_COOKIE_ENDPOINT, {
      method: 'GET',
      credentials: 'include',
    })

    if (!response.ok) {
      return null
    }

    const data = await response.json()
    return data.user_id || null
  } catch {
    return null
  }
}

/**
 * Clear any legacy localStorage auth tokens.
 * Call this once on app startup to migrate users from localStorage to cookies.
 */
export function clearLegacyAuthTokens(): void {
  if (typeof window === 'undefined') return
  
  // Remove old auth_token from localStorage
  const legacyToken = localStorage.getItem('auth_token')
  if (legacyToken) {
    localStorage.removeItem('auth_token')
    console.log('[Auth] Migrated from localStorage to cookies')
  }
}
