/**
 * Production auth gatekeeper.
 *
 * Public pages are available without a session. Protected app routes accept
 * either the Dear Adeline username/PIN student session or a legacy Supabase
 * session. Brain/API requests are allowed through because those endpoints
 * perform their own JWT authorization.
 */
import { createServerClient } from '@supabase/ssr';
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const PUBLIC_PATHS = ['/', '/login', '/signup', '/pricing', '/style-guide'];

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // The source catalog is a parent curation tool, not a student browsing area.
  if (pathname === '/dashboard/resource-vault') {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  if (
    pathname.startsWith('/_next') ||
    pathname.startsWith('/api') ||
    pathname.startsWith('/brain/')
  ) {
    return NextResponse.next();
  }

  if (PUBLIC_PATHS.some((path) => pathname === path)) {
    return NextResponse.next();
  }

  // Preferred production student session: username + PIN → signed Brain JWT
  // stored in an HttpOnly cookie. Validate it server-side before protected UI
  // routes render.
  const studentCookie = request.cookies.get('auth_token')?.value;
  if (studentCookie) {
    try {
      const sessionUrl = new URL('/api/student-auth', request.url);
      const sessionResponse = await fetch(sessionUrl, {
        method: 'GET',
        headers: { cookie: request.headers.get('cookie') ?? '' },
        cache: 'no-store',
      });
      if (sessionResponse.ok) {
        return NextResponse.next();
      }
    } catch {
      // Fall through to Supabase compatibility check, then login redirect.
    }
  }

  // Compatibility path for existing parent/admin Supabase accounts.
  const response = NextResponse.next({ request: { headers: request.headers } });
  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL ?? '',
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? '',
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) => {
            response.cookies.set(name, value, options);
          });
        },
      },
    },
  );

  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('next', pathname);
    return NextResponse.redirect(loginUrl);
  }

  return response;
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)'],
};
