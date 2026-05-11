/**
 * dashboard/layout.tsx — SECONDARY ONBOARDING GATE (server component)
 *
 * Responsibility: verify onboarding completion for /dashboard/*.
 *
 * Contract with middleware.ts:
 *   middleware.ts is the PRIMARY gatekeeper. By the time execution
 *   reaches this layout, middleware has ALREADY confirmed a valid
 *   Supabase session. An unauthenticated request can never reach here.
 *
 * What this layout does:
 *   1. Reads the session from cookies (defense-in-depth — never trust
 *      that middleware ran; always verify before touching the backend).
 *   2. If somehow no session exists → redirect to /login and stop.
 *      The brain API is NEVER called without a confirmed access token.
 *   3. If session exists → call the brain API to check onboardingComplete.
 *   4. Incomplete → server-side redirect('/onboarding') before React mounts.
 *   5. Brain unreachable → let the user through (don't block on infra failure).
 *
 * force-dynamic prevents Vercel from pre-building this layout at build
 * time, which would cause a Supabase cookie-read error in the SSG phase.
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

  // GUARD: No session → redirect immediately. The brain API is never
  // called without a confirmed token. Middleware should have caught this
  // first, but we never assume it did.
  if (!session?.access_token) {
    redirect('/login')
  }

  // Session confirmed. Now check onboarding status.
  let shouldRedirectToOnboarding = false

  try {
    const res = await fetch(`${BRAIN_URL}/brain/api/onboarding`, {
      headers: { Authorization: `Bearer ${session.access_token}` },
      cache: 'no-store',
    })

    if (res.status === 404) {
      // No profile yet — user needs onboarding
      shouldRedirectToOnboarding = true
    } else if (res.ok) {
      const data = (await res.json()) as { user?: { onboardingComplete?: boolean } }
      shouldRedirectToOnboarding = !(data.user?.onboardingComplete ?? false)
    }
    // 5xx or unexpected status → don't block; let user access dashboard
  } catch {
    // Brain unreachable → let through without blocking the user
  }

  if (shouldRedirectToOnboarding) {
    redirect('/onboarding')
  }

  return <>{children}</>
}
