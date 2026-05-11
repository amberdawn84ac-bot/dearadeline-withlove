import { NextRequest, NextResponse } from 'next/server'
import { stripe } from '@/lib/stripe'

const BRAIN_URL = process.env.NEXT_PUBLIC_BRAIN_URL ?? 'https://dearadeline-withlove-production.up.railway.app'

export async function POST(req: NextRequest) {
  const { userId } = await req.json()
  if (!userId) {
    return NextResponse.json({ error: 'userId required' }, { status: 400 })
  }

  // Fetch subscription record from brain
  const subRes  = await fetch(`${BRAIN_URL}/subscriptions/${userId}`)
  const subData = await subRes.json()

  if (!subData?.stripe_customer_id) {
    return NextResponse.json({ error: 'No Stripe customer found' }, { status: 404 })
  }

  try {
    const session = await stripe.billingPortal.sessions.create({
      customer:   subData.stripe_customer_id,
      return_url: `${process.env.NEXT_PUBLIC_APP_URL}/settings`,
    })
    return NextResponse.json({ url: session.url })
  } catch (err) {
    console.error('[Portal Error]', err)
    return NextResponse.json({ error: 'Failed to create portal session' }, { status: 500 })
  }
}
