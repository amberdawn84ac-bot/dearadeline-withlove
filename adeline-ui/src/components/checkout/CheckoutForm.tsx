'use client'

import { useEffect, useState } from 'react'
import { Loader2 } from 'lucide-react'

interface CheckoutFormProps {
  userId:    string
  userEmail?: string
  tier:      string
  billing:   'monthly' | 'yearly'
}

export function CheckoutForm({ userId, userEmail, tier, billing }: CheckoutFormProps) {
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function initCheckout() {
      try {
        const res = await fetch('/api/stripe/create-checkout', {
          method:  'POST',
          headers: { 'Content-Type': 'application/json' },
          body:    JSON.stringify({ userId, userEmail, tier, billing }),
        })
        const data = await res.json()
        if (!res.ok) throw new Error(data.error ?? 'Checkout failed')

        // Redirect to Stripe Checkout
        if (data.url) {
          window.location.href = data.url
        } else {
          setError('No checkout URL returned')
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Checkout error')
        setIsLoading(false)
      }
    }

    initCheckout()
  }, [userId, userEmail, tier, billing])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-center">
          <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-[#BD6809]" />
          <p className="text-sm text-gray-600">Preparing checkout…</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-4 text-center">
        <p className="text-red-600 text-sm">{error}</p>
      </div>
    )
  }

  return null
}
