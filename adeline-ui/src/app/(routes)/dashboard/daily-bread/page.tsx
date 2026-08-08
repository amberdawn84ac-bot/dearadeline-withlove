'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { ArrowLeft, BookOpen, Loader2 } from 'lucide-react'

type DailyBread = {
  verse: string
  reference: string
  original: string
  originalMeaning: string
  translationNote?: string | null
  context: string
}

export default function DailyBreadPage() {
  const [bread, setBread] = useState<DailyBread | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false

    async function load() {
      try {
        const response = await fetch('/brain/daily-bread', { cache: 'no-store' })
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        const data = await response.json() as DailyBread
        if (!cancelled) setBread(data)
      } catch {
        if (!cancelled) setError('Daily Bread could not load right now. Try again in a moment.')
      }
    }

    void load()
    return () => { cancelled = true }
  }, [])

  return (
    <main className="min-h-screen bg-[#fbf7ec] px-5 py-8 text-[#2f4731] sm:px-8">
      <div className="mx-auto max-w-3xl">
        <Link href="/dashboard" className="inline-flex items-center gap-2 text-sm text-[#6f624f] hover:text-[#2f4731]">
          <ArrowLeft size={16} /> Back to Adeline
        </Link>

        <div className="mt-8 rounded-[30px] border border-[#d7c8aa] bg-[#fffdf7] p-7 shadow-[0_18px_50px_rgba(67,51,31,.08)] sm:p-10">
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#2f4731] text-white"><BookOpen size={22} /></div>
            <div>
              <p className="text-[10px] uppercase tracking-[.22em] text-[#9b8060]">Today&apos;s Daily Bread</p>
              <h1 className="text-4xl text-[#2f4731]" style={{ fontFamily: 'var(--font-emilys-candy)' }}>A word worth carrying</h1>
            </div>
          </div>

          {!bread && !error && (
            <div className="flex min-h-[300px] items-center justify-center text-[#7d715f]"><Loader2 className="mr-2 animate-spin" size={18} /> Opening today&apos;s passage...</div>
          )}

          {error && <p className="mt-10 rounded-2xl border border-[#d9b9b1] bg-[#fff2ee] p-5 text-sm text-[#8a5148]">{error}</p>}

          {bread && (
            <div className="mt-10 space-y-8">
              <div>
                <blockquote className="text-2xl leading-10 text-[#2f4731] sm:text-3xl sm:leading-[1.55]">“{bread.verse}”</blockquote>
                <p className="mt-4 text-sm font-semibold uppercase tracking-[.16em] text-[#b56d27]">{bread.reference}</p>
              </div>

              <section className="rounded-[24px] bg-[#f5eddc] p-6">
                <p className="text-[10px] uppercase tracking-[.18em] text-[#8c7152]">Original language</p>
                <h2 className="mt-2 text-3xl text-[#2f4731]" style={{ fontFamily: 'var(--font-emilys-candy)' }}>{bread.original}</h2>
                <p className="mt-3 text-sm leading-7 text-[#5e584c]">{bread.originalMeaning}</p>
              </section>

              {bread.translationNote && (
                <section>
                  <h2 className="text-xl font-semibold">What the English can flatten</h2>
                  <p className="mt-2 text-sm leading-7 text-[#5e584c]">{bread.translationNote}</p>
                </section>
              )}

              <section>
                <h2 className="text-xl font-semibold">The world around the words</h2>
                <p className="mt-2 text-sm leading-7 text-[#5e584c]">{bread.context}</p>
              </section>
            </div>
          )}
        </div>
      </div>
    </main>
  )
}
