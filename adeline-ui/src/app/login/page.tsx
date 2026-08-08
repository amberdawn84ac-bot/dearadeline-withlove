'use client'

import { useEffect, useState, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import Image from 'next/image'
import { Loader2, Eye, EyeOff } from 'lucide-react'
import { supabase } from '@/lib/supabase'
import { setAuthCookie } from '@/lib/auth-cookies'

type Mode = 'login' | 'signup'

function LoginContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const requestedMode = searchParams.get('mode') === 'signup' ? 'signup' : 'login'
  const [mode, setMode] = useState<Mode>(requestedMode)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const inviteCode = searchParams.get('invite')

  useEffect(() => {
    setMode(requestedMode)
  }, [requestedMode])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      if (mode === 'signup') {
        const { data, error: signUpError } = await supabase.auth.signUp({ email, password })
        if (signUpError) throw signUpError
        if (!data.session) {
          setError('Check your email for a confirmation link, then come back and log in.')
          setLoading(false)
          return
        }
        await setAuthCookie(data.session.access_token)
        router.push(inviteCode ? `/onboarding?invite=${inviteCode}` : '/onboarding')
      } else {
        const { data, error: signInError } = await supabase.auth.signInWithPassword({ email, password })
        if (signInError) throw signInError
        if (!data.session) throw new Error('No session returned')
        const token = data.session.access_token
        await setAuthCookie(token)
        try {
          const profileRes = await fetch(`/brain/api/onboarding?_=${Date.now()}`, {
            headers: { Authorization: `Bearer ${token}`, 'Cache-Control': 'no-cache' },
          })
          if (profileRes.ok) {
            const profileData = await profileRes.json()
            if (profileData?.user?.onboardingComplete) {
              router.push('/dashboard')
              return
            }
          }
        } catch {
          // The dashboard gate will re-check.
        }
        router.push('/onboarding')
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#FFFEF7] flex flex-col items-center justify-center px-6">
      <Link href="/" className="flex items-center gap-3 mb-10">
        <Image src="/adeline-nav.png" alt="Adeline" width={44} height={44} className="rounded-xl shadow-lg -rotate-3" />
        <span className="text-2xl font-bold text-[#2F4731]" style={{ fontFamily: 'var(--font-emilys-candy), "Emilys Candy", cursive' }}>Dear Adeline</span>
      </Link>

      <div className="w-full max-w-sm bg-white rounded-2xl border-2 border-[#E7DAC3] p-8 shadow-sm">
        <h1 className="text-2xl font-bold text-[#2F4731] text-center mb-1">{mode === 'login' ? 'Welcome back' : 'Create your account'}</h1>
        <p className="text-sm text-[#2F4731]/60 text-center mb-6">
          {mode === 'login' ? 'Come back to Adeline.' : 'Start free. You can choose a paid plan later if you want one.'}
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-xs font-semibold text-[#2F4731] mb-1.5">Email</label>
            <input id="email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" autoComplete="email" className="w-full px-4 py-2.5 rounded-xl border border-[#E7DAC3] text-sm text-[#2F4731] bg-white focus:outline-none focus:border-[#BD6809] transition-colors" />
          </div>
          <div>
            <label htmlFor="password" className="block text-xs font-semibold text-[#2F4731] mb-1.5">Password</label>
            <div className="relative">
              <input id="password" type={showPassword ? 'text' : 'password'} required minLength={6} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="At least 6 characters" autoComplete={mode === 'login' ? 'current-password' : 'new-password'} className="w-full px-4 py-2.5 rounded-xl border border-[#E7DAC3] text-sm text-[#2F4731] bg-white focus:outline-none focus:border-[#BD6809] transition-colors pr-10" />
              <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-[#2F4731]/40 hover:text-[#2F4731]" aria-label={showPassword ? 'Hide password' : 'Show password'}>
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {error && <p className="text-xs text-[#9A3F4A] bg-[#9A3F4A]/10 rounded-lg px-3 py-2">{error}</p>}

          <button type="submit" disabled={loading} className="w-full py-3 rounded-xl bg-[#2F4731] text-white font-bold text-sm hover:bg-[#243828] disabled:opacity-50 transition-colors flex items-center justify-center gap-2">
            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
            {mode === 'login' ? 'Sign In' : 'Create Free Account'}
          </button>
        </form>

        <div className="mt-6 text-center text-sm text-[#2F4731]/60">
          {mode === 'login' ? (
            <>Don&apos;t have an account? <button onClick={() => { setMode('signup'); setError('') }} className="text-[#BD6809] font-semibold hover:underline">Create one free</button></>
          ) : (
            <>Already have an account? <button onClick={() => { setMode('login'); setError('') }} className="text-[#BD6809] font-semibold hover:underline">Log in</button></>
          )}
        </div>
      </div>

      <p className="mt-6 text-xs text-[#2F4731]/40">Paid plans are optional. <Link href="/pricing" className="text-[#BD6809] hover:underline font-medium">See plan differences</Link></p>
    </div>
  )
}

export default function LoginPage() {
  return <Suspense fallback={<div className="min-h-screen bg-[#FFFEF7]" />}><LoginContent /></Suspense>
}
