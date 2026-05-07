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

const PUBLIC_ROUTES = ['/login', '/signup', '/onboarding', '/'];
const PROTECTED_ROUTES = ['/dashboard', '/settings'];

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

        const response = await fetch(`/brain?_=${Date.now()}`, {
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

        const data = await response.json();
        const onboardingComplete = data.user?.onboardingComplete ?? false;

        // If on protected route and not complete, go to onboarding
        if (!onboardingComplete) {
          window.location.href = '/onboarding';
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
