/**
 * Dashboard layout — server component.
 *
 * Runs before any client code mounts. Checks whether the authenticated user has
 * completed onboarding and redirects server-side if not. This is the correct fix
 * for the /dashboard ↔ /onboarding ping-pong: the redirect happens once, at the
 * server, before React has a chance to run.
 */
import { redirect } from 'next/navigation'
import { cookies } from 'next/headers'
import { createServerClient } from '@supabase/ssr'

export const dynamic = 'force-dynamic'

const BRAIN_URL = (
  process.env.BRAIN_INTERNAL_URL ||
  process.env.BRAIN_URL ||
  process.env.NEXT_PUBLIC_BRAIN_URL ||
  'http://localhost:8000'
).replace(/\/$/, '')

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const cookieStore = await cookies()

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL ?? '',
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? '',
    {
      cookies: {
        getAll() {
          return cookieStore.getAll()
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value, options }) => {
            cookieStore.set(name, value, options)
          })
        },
      },
    },
  )

  const {
    data: { session },
  } = await supabase.auth.getSession()

  if (!session?.access_token) {
    redirect('/login')
  }

  let shouldRedirectToOnboarding = false

  try {
    const res = await fetch(`${BRAIN_URL}/brain/api/onboarding`, {
      headers: { Authorization: `Bearer ${session.access_token}` },
      cache: 'no-store',
    })

    if (res.status === 404) {
      shouldRedirectToOnboarding = true
    } else if (res.ok) {
      const data = (await res.json()) as { user?: { onboardingComplete?: boolean } }
      shouldRedirectToOnboarding = !(data.user?.onboardingComplete ?? false)
    }
    // Any other non-ok status (5xx etc.) — don't block; let user access dashboard
  } catch {
    // Brain unreachable — let through without blocking the user
  }

  if (shouldRedirectToOnboarding) {
    redirect('/onboarding')
  }

  return <>{children}</>
}
