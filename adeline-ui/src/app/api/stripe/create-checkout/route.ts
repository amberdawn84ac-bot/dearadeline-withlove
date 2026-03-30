import { NextRequest, NextResponse } from 'next/server'
import { stripe, STRIPE_PRICES } from '@/lib/stripe'

export async function POST(req: NextRequest) {
  const { userId, userEmail, tier, billing } = await req.json()

  if (!userId) {
    return NextResponse.json({ error: 'userId required' }, { status: 400 })
  }

  const validTiers = ['STUDENT', 'PARENT', 'TEACHER']
  if (!validTiers.includes(tier)) {
    return NextResponse.json({ error: 'Invalid tier' }, { status: 400 })
  }

  const priceKey = `${tier}_${(billing ?? 'MONTHLY').toUpperCase()}` as keyof typeof STRIPE_PRICES
  const priceId  = STRIPE_PRICES[priceKey]
  if (!priceId) {
    return NextResponse.json({ error: 'Price ID not configured' }, { status: 400 })
  }

  try {
    const customer = await stripe.customers.create({
      email:    userEmail,
      metadata: { userId },
    })

    const session = await stripe.checkout.sessions.create({
      customer:             customer.id,
      mode:                 'subscription',
      payment_method_types: ['card'],
      line_items: [{ price: priceId, quantity: 1 }],
      subscription_data: {
        trial_period_days: 7,
        metadata: { userId, tier },
      },
      success_url: `${process.env.NEXT_PUBLIC_APP_URL}/dashboard?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url:  `${process.env.NEXT_PUBLIC_APP_URL}/pricing`,
      metadata:    { userId, tier },
      allow_promotion_codes: true,
    })

    return NextResponse.json({ sessionId: session.id, url: session.url, clientSecret: session.client_secret })
  } catch (err) {
    console.error('[Stripe Checkout Error]', err)
    const msg = err instanceof Error ? err.message : 'Unknown error'
    return NextResponse.json({ error: msg }, { status: 500 })
  }
}
