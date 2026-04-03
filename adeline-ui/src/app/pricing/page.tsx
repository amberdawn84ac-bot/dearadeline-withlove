'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { X } from 'lucide-react'
import { CheckoutForm } from '@/components/checkout/CheckoutForm'

type Billing = 'monthly' | 'yearly'

const TIERS = [
  {
    id: 'FREE',
    name: 'Free',
    price: { monthly: 0, yearly: 0 },
    description: 'Try Adeline with the basics',
    features: [
      'Unlimited lessons',
      '1 student profile',
      'All 10 curriculum tracks',
      'Join learning clubs',
      '✗ No Learning Path',
      '✗ No Daily Journal',
      '✗ No Projects catalog',
      '✗ No Transcripts',
    ],
    cta: 'Start Free',
    popular: false,
    trial: false,
  },
  {
    id: 'STUDENT',
    name: 'Student',
    price: { monthly: 9.99, yearly: 107.89 },
    description: 'Full access for one learner',
    features: [
      'Everything in Free, plus:',
      '✓ Learning Path + ZPD engine',
      '✓ Daily Journal',
      '✓ Projects catalog',
      '✓ Full lesson history',
      '✓ Progress tracking',
    ],
    cta: 'Start 7-Day Trial',
    popular: true,
    trial: true,
  },
  {
    id: 'FAMILY',
    name: 'Family',
    price: { monthly: 29.99, yearly: 323.89 },
    description: 'For homeschool families',
    features: [
      'Everything in Student, plus:',
      '✓ Up to 5 students',
      '✓ Parent dashboard',
      '✓ PDF transcripts',
      '✓ Portfolio builder',
      '+ $2.99/mo per extra student',
    ],
    cta: 'Start 7-Day Trial',
    popular: false,
    trial: true,
  },
  {
    id: 'COOP',
    name: 'Co-op',
    price: { monthly: 49.99, yearly: 539.89 },
    description: 'For classrooms and co-ops',
    features: [
      'Everything in Family, plus:',
      '✓ Up to 40 students',
      '✓ Classroom management',
      '✓ Bulk progress reports',
      '✓ Student grouping',
      '+ $2.99/mo per extra student',
    ],
    cta: 'Start 7-Day Trial',
    popular: false,
    trial: true,
  },
]

// TODO: replace with real user from session/auth
const DEMO_USER = { id: 'demo-user-001', email: 'demo@example.com' }

export default function PricingPage() {
  const router = useRouter()
  const [billing, setBilling]   = useState<Billing>('monthly')
  const [checkout, setCheckout] = useState<string | null>(null)

  return (
    <div className="min-h-screen bg-[#FFFEF7] py-16 px-6">
      {/* Embedded checkout modal */}
      {checkout && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
          onClick={(e) => { if (e.target === e.currentTarget) setCheckout(null) }}
        >
          <div className="relative bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <button
              onClick={() => setCheckout(null)}
              className="absolute top-4 right-4 z-10 p-1 rounded-full text-gray-400 hover:text-gray-700"
            >
              <X className="w-5 h-5" />
            </button>
            <div className="p-2">
              <CheckoutForm
                userId={DEMO_USER.id}
                userEmail={DEMO_USER.email}
                tier={checkout}
                billing={billing}
              />
            </div>
          </div>
        </div>
      )}

      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-[#2F4731] mb-3">Choose Your Plan</h1>
          <p className="text-[#4B3424] text-lg mb-8">
            Start free — or try any paid plan for 7 days at no charge.
          </p>

          {/* Billing toggle */}
          <div className="inline-flex rounded-xl border border-[#E7DAC3] overflow-hidden">
            {(['monthly', 'yearly'] as Billing[]).map((b) => (
              <button
                key={b}
                onClick={() => setBilling(b)}
                className={`px-6 py-3 font-semibold text-sm transition-colors relative ${
                  billing === b
                    ? 'bg-[#BD6809] text-white'
                    : 'bg-white text-[#2F4731] hover:bg-[#FFF8EE]'
                }`}
              >
                {b === 'yearly' ? (
                  <>Yearly <span className="ml-1 text-xs bg-[#2F4731] text-white px-2 py-0.5 rounded-full">Save 10%</span></>
                ) : 'Monthly'}
              </button>
            ))}
          </div>
        </div>

        {/* Tier cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {TIERS.map((tier) => (
            <div
              key={tier.id}
              className={`relative rounded-2xl p-6 bg-white flex flex-col ${
                tier.popular ? 'border-2 border-[#BD6809] shadow-lg' : 'border border-[#E7DAC3]'
              }`}
            >
              {tier.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-[#BD6809] text-white text-xs font-bold px-4 py-1 rounded-full">
                  Most Popular
                </div>
              )}

              <h3 className="text-xl font-bold text-[#2F4731] mb-1">{tier.name}</h3>
              <p className="text-sm text-[#4B3424] mb-4">{tier.description}</p>

              <div className="mb-6">
                <span className="text-3xl font-bold text-[#2F4731]">
                  ${billing === 'monthly' ? tier.price.monthly : tier.price.yearly}
                </span>
                {tier.price.monthly > 0 && (
                  <span className="text-[#4B3424] text-sm ml-1">
                    {billing === 'monthly' ? '/mo' : '/yr'}
                  </span>
                )}
                {billing === 'yearly' && tier.price.yearly > 0 && (
                  <div className="text-xs text-[#BD6809] font-semibold mt-1">
                    ${(tier.price.yearly / 12).toFixed(2)}/mo billed annually
                  </div>
                )}
              </div>

              <ul className="space-y-2 mb-6 flex-1">
                {tier.features.map((f, i) => (
                  <li key={i} className="text-sm text-[#121B13]">{f}</li>
                ))}
              </ul>

              <button
                onClick={() => tier.id === 'FREE' ? router.push('/dashboard') : setCheckout(tier.id)}
                className={`w-full py-3 rounded-xl font-bold text-sm transition-colors ${
                  tier.popular
                    ? 'bg-[#BD6809] text-white hover:bg-[#a05a08]'
                    : 'bg-[#2F4731] text-white hover:bg-[#243828]'
                }`}
              >
                {tier.cta}
              </button>
            </div>
          ))}
        </div>

        <p className="text-center text-sm text-[#4B3424] mt-8">
          All paid plans include a 7-day free trial. Cancel anytime.
        </p>
      </div>
    </div>
  )
}
