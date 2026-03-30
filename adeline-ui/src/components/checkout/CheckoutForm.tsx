'use client'

import { useCallback } from 'react'
import { loadStripe } from '@stripe/stripe-js'
import { EmbeddedCheckout, EmbeddedCheckoutProvider } from '@stripe/react-stripe-js'

const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY!)

interface CheckoutFormProps {
  userId:    string
  userEmail?: string
  tier:      string
  billing:   'monthly' | 'yearly'
}

export function CheckoutForm({ userId, userEmail, tier, billing }: CheckoutFormProps) {
  const fetchClientSecret = useCallback(async () => {
    const res = await fetch('/api/stripe/create-checkout', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ userId, userEmail, tier, billing }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.error ?? 'Checkout failed')
    return data.clientSecret as string
  }, [userId, userEmail, tier, billing])

  return (
    <EmbeddedCheckoutProvider stripe={stripePromise} options={{ fetchClientSecret }}>
      <EmbeddedCheckout />
    </EmbeddedCheckoutProvider>
  )
}
