'use client';

import { useEffect } from 'react';
import { usePathname } from 'next/navigation';
import { supabase } from '@/lib/supabase';

/**
 * OnboardingGate: Ensures user completes onboarding before accessing protected routes.
 *
 * Public routes (no gate):
 * - /login
 * - /signup
 * - /onboarding
 * - / (landing)
 *
 * Protected routes (gate check):
 * - /dashboard
 * - /settings
 * - All routes under /dashboard/*
 *
 * Behavior:
 * - If user is on a protected route and onboarding is not complete, redirect to /onboarding
 * - If user is on /onboarding and onboarding is already complete, redirect to /dashboard
 */

const PUBLIC_ROUTES = ['/login', '/signup', '/onboarding', '/', '/coppa-pending', '/coppa-verify'];
const PROTECTED_ROUTES = ['/dashboard', '/settings'];
const UNDER_13_GRADES = new Set(['K', '1', '2', '3', '4', '5', '6', '7']);

export function OnboardingGate() {
  const pathname = usePathname();

  useEffect(() => {
    // Skip gate checks if route is explicitly public
    const isPublicRoute = PUBLIC_ROUTES.includes(pathname) || pathname === '/';
    if (isPublicRoute && pathname !== '/onboarding') {
      return;
    }

    // Check if route is protected
    const isProtectedRoute = PROTECTED_ROUTES.some(
      (route) => pathname === route || pathname.startsWith(route + '/')
    );

    if (!isProtectedRoute && pathname !== '/onboarding') {
      return;
    }

    // Check onboarding status
    const checkOnboarding = async () => {
      try {
        const { data: sessionData, error: sessionError } = await supabase.auth.getSession();
        if (sessionError || !sessionData.session?.access_token) {
          if (pathname !== '/login') {
            window.location.href = '/login';
          }
          return;
        }
        const token = sessionData.session.access_token;

        // Only gate-check protected routes — /onboarding handles its own redirect to /dashboard
        if (!isProtectedRoute) {
          return;
        }

        const response = await fetch(`/brain/api/onboarding?_=${Date.now()}`, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
          },
        });

        if (response.status === 401) {
          window.location.href = '/login';
          return;
        }

        if (response.status === 404) {
          // No profile yet — user needs onboarding
          window.location.href = '/onboarding';
          return;
        }

        if (!response.ok) {
          return;
        }

        const data = await response.json() as {
          user?: { onboardingComplete?: boolean; gradeLevel?: string; coppaVerified?: boolean };
        };
        const user = data.user;

        if (!user?.onboardingComplete) {
          window.location.href = '/onboarding';
          return;
        }

        // COPPA gate: grades K-7 must have parent email verification
        if (
          user.gradeLevel &&
          UNDER_13_GRADES.has(user.gradeLevel) &&
          !user.coppaVerified &&
          pathname !== '/coppa-pending'
        ) {
          window.location.href = '/coppa-pending';
          return;
        }
      } catch (err) {
        console.error('Error in onboarding gate:', err);
        // Don't block on error — let user retry
      }
    };

    checkOnboarding();
  }, [pathname]);

  return null;
}
