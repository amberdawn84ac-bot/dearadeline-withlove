/**
 * middleware.ts — PRIMARY AUTH GATEKEEPER
 *
 * TEMPORARY PREVIEW MODE:
 *   /dashboard and /dashboard/* are public while the visual/product flow is being built.
 *   Remove the dashboard preview exception when backend auth is ready for the final flow.
 */
import { createServerClient } from '@supabase/ssr'
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

const PUBLIC_PATHS = ['/', '/login', '/signup', '/pricing', '/style-guide']

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Next.js internals, static files, and brain auth endpoints always pass through.
  if (
    pathname.startsWith('/_next') ||
    pathname.startsWith('/api') ||
    pathname.startsWith('/brain/auth/')
  ) {
    return NextResponse.next()
  }

  // Temporary visual/product preview: landing can enter the dashboard directly.
  if (pathname === '/dashboard' || pathname.startsWith('/dashboard/')) {
    return NextResponse.next()
  }

  // Public paths always pass through — no session check.
  if (PUBLIC_PATHS.some((p) => pathname === p)) {
    return NextResponse.next()
  }

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

  const {
    data: { session },
  } = await supabase.auth.getSession()

  if (!session) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  return response
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)'],
}
