/**
 * middleware.ts — PRIMARY AUTH GATEKEEPER
 *
 * This is the single source of truth for authentication redirects.
 * It runs at the server edge before any React component, layout, or
 * Server Component executes. Rules:
 *
 *   • Public paths (/, /login, /signup, /pricing, /style-guide)
 *     → always pass through, no session check.
 *
 *   • All other paths (protected)
 *     → require a valid Supabase session in cookies.
 *     → unauthenticated → redirect to /login immediately.
 *
 * Onboarding completeness is NOT checked here — that is handled
 * server-side in dashboard/layout.tsx after the session is confirmed.
 * This separation keeps middleware fast (one cookie read, no external
 * network calls) and gives the dashboard layout a clean, guaranteed
 * context: if it runs, the user IS authenticated.
 */
import { createServerClient } from '@supabase/ssr'
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

const PUBLIC_PATHS = ['/', '/login', '/signup', '/pricing', '/style-guide']

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Next.js internals and static files always pass through
  if (pathname.startsWith('/_next') || pathname.startsWith('/api')) {
    return NextResponse.next()
  }

  // Public paths always pass through — no session check
  if (PUBLIC_PATHS.some((p) => pathname === p)) {
    return NextResponse.next()
  }

  // Build the mutable response so the cookie adapter can refresh tokens
  const response = NextResponse.next({ request: { headers: request.headers } })

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL ?? '',
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? '',
    {
      cookies: {
        getAll() {
          return request.cookies.getAll()
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) => {
            response.cookies.set(name, value, options)
          })
        },
      },
    },
  )

  // getSession reads from cookies — fast, zero external network calls.
  const {
    data: { session },
  } = await supabase.auth.getSession()

  if (!session) {
    // No session → middleware handles the redirect. No layout or page code runs.
    return NextResponse.redirect(new URL('/login', request.url))
  }

  // Session confirmed → pass through. dashboard/layout.tsx handles
  // the finer-grained onboarding-completion check for /dashboard/*.
  return response
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)'],
}
