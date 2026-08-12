/**
 * dashboard/layout.tsx — onboarding/auth gate for the dashboard.
 *
 * TEMPORARY PREVIEW MODE:
 * The dashboard is intentionally viewable without authentication while the
 * landing/dashboard experience is being finalized. Auth and onboarding checks
 * remain here for signed-in users and can become mandatory again by restoring
 * the redirect for a missing session.
 */
import { redirect } from 'next/navigation'
import { cookies } from 'next/headers'
import { createServerClient } from '@supabase/ssr'

export const dynamic = 'force-dynamic'

const BRAIN_URL = (
  process.env.BRAIN_INTERNAL_URL ||
  process.env.BRAIN_URL ||
  process.env.NEXT_PUBLIC_BRAIN_URL ||
  'https://dearadeline-withlove-production.up.railway.app'
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

  // Preview mode: no session is allowed through for now.
  if (!session?.access_token) {
    return <>{children}</>
  }

  let shouldRedirectToOnboarding = false

  try {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 8000)

    const res = await fetch(`${BRAIN_URL}/brain/api/onboarding`, {
      headers: { Authorization: `Bearer ${session.access_token}` },
      cache: 'no-store',
      signal: controller.signal,
    })
    clearTimeout(timeoutId)

    if (res.ok) {
      const data = (await res.json()) as { user?: { onboardingComplete?: boolean } }
      if (data.user && data.user.onboardingComplete === false) {
        shouldRedirectToOnboarding = true
      }
    }
  } catch {
    // Brain unreachable or request timed out: don't block dashboard rendering.
  }

  if (shouldRedirectToOnboarding) {
    redirect('/onboarding')
  }

  return <>{children}</>
}
