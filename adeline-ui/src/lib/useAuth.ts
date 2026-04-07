'use client'

import { useState, useEffect } from 'react'
import { supabase } from './supabase'

interface AuthUser {
  id: string
  email: string | null
}

export function useAuth() {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Check current session
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session?.user) {
        setUser({ id: session.user.id, email: session.user.email ?? null })
        // Keep localStorage in sync for brain API calls
        localStorage.setItem('auth_token', session.access_token)
      } else {
        setUser(null)
      }
      setLoading(false)
    })

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session?.user) {
        setUser({ id: session.user.id, email: session.user.email ?? null })
        localStorage.setItem('auth_token', session.access_token)
      } else {
        setUser(null)
        localStorage.removeItem('auth_token')
      }
    })

    return () => subscription.unsubscribe()
  }, [])

  return { user, loading }
}
