import { NextRequest, NextResponse } from 'next/server'
import { stripe } from '@/lib/stripe'
import Stripe from 'stripe'

const BRAIN_URL = process.env.NEXT_PUBLIC_BRAIN_URL ?? 'http://localhost:8000'

export async function POST(req: NextRequest) {
  const body = await req.text()
  const sig  = req.headers.get('stripe-signature')

  if (!sig || !process.env.STRIPE_WEBHOOK_SECRET) {
    return NextResponse.json({ error: 'Missing signature' }, { status: 400 })
  }

  let event: Stripe.Event
  try {
    event = stripe.webhooks.constructEvent(body, sig, process.env.STRIPE_WEBHOOK_SECRET)
  } catch (err) {
    console.error('[Webhook] Signature verification failed', err)
    return NextResponse.json({ error: 'Invalid signature' }, { status: 400 })
  }

  try {
    switch (event.type) {
      case 'checkout.session.completed': {
        const session = event.data.object as Stripe.Checkout.Session
        await handleCheckoutCompleted(session)
        break
      }
      case 'customer.subscription.updated': {
        const sub = event.data.object as Stripe.Subscription
        await handleSubscriptionUpdated(sub)
        break
      }
      case 'customer.subscription.deleted': {
        const sub = event.data.object as Stripe.Subscription
        await handleSubscriptionDeleted(sub)
        break
      }
      case 'invoice.payment_failed': {
        const invoice = event.data.object as Stripe.Invoice
        console.warn(`[Payment] Failed invoice=${invoice.id}`)
        break
      }
      default:
        console.log(`[Webhook] Unhandled event type: ${event.type}`)
    }
    return NextResponse.json({ received: true })
  } catch (err) {
    console.error('[Webhook] Handler error', err)
    return NextResponse.json({ error: 'Handler failed' }, { status: 500 })
  }
}

async function handleCheckoutCompleted(session: Stripe.Checkout.Session) {
  const userId = session.metadata?.userId
  const tier   = session.metadata?.tier as string
  if (!userId || !tier) throw new Error('Missing userId or tier in session metadata')

  const sub = await stripe.subscriptions.retrieve(session.subscription as string) as Stripe.Subscription & { current_period_end: number }

  await fetch(`${BRAIN_URL}/subscriptions/upsert`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id:                userId,
      stripe_customer_id:     session.customer as string,
      stripe_subscription_id: sub.id,
      stripe_price_id:        sub.items.data[0].price.id,
      tier,
      status:                 'ACTIVE',
      current_period_end:     new Date(sub.current_period_end * 1000).toISOString(),
      cancel_at_period_end:   false,
    }),
  })
  console.log(`[Checkout] Subscription created user=${userId} tier=${tier}`)
}

async function handleSubscriptionUpdated(sub: Stripe.Subscription & { current_period_end?: number }) {
  // Find which user owns this subscription
  const existing = await fetch(`${BRAIN_URL}/subscriptions/upsert`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      user_id:                sub.metadata?.userId ?? 'unknown',
      stripe_customer_id:     sub.customer as string,
      stripe_subscription_id: sub.id,
      stripe_price_id:        sub.items.data[0].price.id,
      tier:                   sub.metadata?.tier ?? 'STUDENT',
      status:                 sub.status === 'active' ? 'ACTIVE' : 'PAST_DUE',
      current_period_end:     sub.current_period_end
        ? new Date(sub.current_period_end * 1000).toISOString()
        : new Date().toISOString(),
      cancel_at_period_end:   sub.cancel_at_period_end,
    }),
  })
  console.log(`[Subscription] Updated id=${sub.id}`)
}

async function handleSubscriptionDeleted(sub: Stripe.Subscription) {
  await fetch(`${BRAIN_URL}/subscriptions/cancel`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ stripe_subscription_id: sub.id }),
  })
  console.log(`[Subscription] Canceled id=${sub.id}`)
}
