import 'server-only'

import Stripe from 'stripe'

export const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!)

// Price IDs — create these in Stripe Dashboard, then set env vars
export const STRIPE_PRICES = {
  STUDENT_MONTHLY: process.env.STRIPE_PRICE_STUDENT_MONTHLY || '',
  STUDENT_YEARLY:  process.env.STRIPE_PRICE_STUDENT_YEARLY  || '',
  FAMILY_MONTHLY:  process.env.STRIPE_PRICE_FAMILY_MONTHLY  || '',
  FAMILY_YEARLY:   process.env.STRIPE_PRICE_FAMILY_YEARLY   || '',
  COOP_MONTHLY:    process.env.STRIPE_PRICE_COOP_MONTHLY    || '',
  COOP_YEARLY:     process.env.STRIPE_PRICE_COOP_YEARLY     || '',
} as const

export type TierName = 'FREE' | 'STUDENT' | 'FAMILY' | 'COOP'

export const TIER_LIMITS: Record<TierName, {
  students:          number
  canCreateClubs:    boolean
  hasParentDashboard: boolean
  hasTranscripts:    boolean
  hasLearningPath:   boolean
  hasJournal:        boolean
  hasProjects:       boolean
}> = {
  FREE: {
    students:          1,
    canCreateClubs:    true,
    hasParentDashboard: false,
    hasTranscripts:    false,
    hasLearningPath:   false,
    hasJournal:        false,
    hasProjects:       false,
  },
  STUDENT: {
    students:          1,
    canCreateClubs:    true,
    hasParentDashboard: false,
    hasTranscripts:    false,
    hasLearningPath:   true,
    hasJournal:        true,
    hasProjects:       true,
  },
  FAMILY: {
    students:          5,
    canCreateClubs:    true,
    hasParentDashboard: true,
    hasTranscripts:    true,
    hasLearningPath:   true,
    hasJournal:        true,
    hasProjects:       true,
  },
  COOP: {
    students:          40,
    canCreateClubs:    true,
    hasParentDashboard: true,
    hasTranscripts:    true,
    hasLearningPath:   true,
    hasJournal:        true,
    hasProjects:       true,
  },
}
