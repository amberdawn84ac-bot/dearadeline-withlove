'use client'

import { useState, useEffect } from 'react'
import { supabase } from './supabase'
import { setAuthCookie, clearAuthCookie, clearLegacyAuthTokens } from './auth-cookies'

interface AuthUser {
  id: string
  email: string | null
}

export function useAuth() {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Clear legacy localStorage tokens on first load
    clearLegacyAuthTokens()

    // Check current session
    supabase.auth.getSession().then(async ({ data: { session } }) => {
      if (session?.user) {
        setUser({ id: session.user.id, email: session.user.email ?? null })
        // Set cookie for brain API calls (production-grade auth)
        try {
          await setAuthCookie(session.access_token)
        } catch (e) {
          console.error('[useAuth] Failed to set auth cookie:', e)
        }
      } else {
        setUser(null)
      }
      setLoading(false)
    })

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (_event, session) => {
      if (session?.user) {
        setUser({ id: session.user.id, email: session.user.email ?? null })
        // Set cookie for brain API calls
        try {
          await setAuthCookie(session.access_token)
        } catch (e) {
          console.error('[useAuth] Failed to set auth cookie:', e)
        }
      } else {
        setUser(null)
        // Clear cookie on logout
        await clearAuthCookie()
      }
    })

    return () => subscription.unsubscribe()
  }, [])

  return { user, loading }
}
