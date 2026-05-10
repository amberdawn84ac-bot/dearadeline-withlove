import { createServerClient } from '@supabase/ssr'
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

const PUBLIC_PATHS = ['/', '/login', '/signup', '/pricing', '/style-guide']

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Static assets and Next.js internals always pass through
  if (pathname.startsWith('/_next') || pathname.startsWith('/api')) {
    return NextResponse.next()
  }

  // Public marketing/auth paths always pass through
  if (PUBLIC_PATHS.some((p) => pathname === p)) {
    return NextResponse.next()
  }

  // Build the response object that the cookie adapter will mutate
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

  // getSession reads from cookies — fast, no external network call.
  // We validate authenticity further in Server Components via getUser() where needed.
  const {
    data: { session },
  } = await supabase.auth.getSession()

  if (!session) {
    // Unauthenticated request to a protected route → send to login
    return NextResponse.redirect(new URL('/login', request.url))
  }

  return response
}

export const config = {
  // Run on all paths except static files and Next.js internals
  matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)'],
}
