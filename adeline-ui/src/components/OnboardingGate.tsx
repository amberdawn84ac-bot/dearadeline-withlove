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
        // Get live session from Supabase (more reliable than localStorage)
        const { data: sessionData, error: sessionError } = await supabase.auth.getSession();

        if (sessionError) {
          console.error('[OnboardingGate] Supabase session error:', sessionError);
          if (pathname !== '/login') {
            window.location.href = '/login';
          }
          return;
        }

        const token = sessionData.session?.access_token;

        // Unauthenticated users should go to login
        if (!token) {
          console.log('[OnboardingGate] No token, redirecting to login');
          if (pathname !== '/login') {
            window.location.href = '/login';
          }
          return;
        }

        // Add cache-busting to prevent stale reads after onboarding completion
        const cacheBuster = Date.now();
        const url = `/brain/api/onboarding?_=${cacheBuster}`;
        console.log('[OnboardingGate] Fetching:', url, 'pathname:', pathname);

        const response = await fetch(url, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
          },
        });

        console.log('[OnboardingGate] Response status:', response.status, 'statusText:', response.statusText);

        if (response.status === 401) {
          console.log('[OnboardingGate] 401 Unauthorized, redirecting to login');
          window.location.href = '/login';
          return;
        }

        if (response.status === 404) {
          // 404 means user profile doesn't exist yet - needs onboarding
          console.log('[OnboardingGate] 404 User not found, needs onboarding');
          if (isProtectedRoute) {
            console.log('[OnboardingGate] Protected route without profile, redirecting to /onboarding');
            window.location.href = '/onboarding';
          }
          return;
        }

        if (!response.ok) {
          console.error('[OnboardingGate] Error checking onboarding status:', response.status, response.statusText);
          // Log response body for debugging
          try {
            const errorBody = await response.text();
            console.error('[OnboardingGate] Error body:', errorBody);
          } catch {
            // Ignore error reading body
          }
          return;
        }

        const data = await response.json();
        console.log('[OnboardingGate] Response data:', data);

        const userProfile = data.user;
        if (!userProfile) {
          console.error('[OnboardingGate] No user in response data');
          return;
        }

        const onboardingComplete = userProfile.onboardingComplete;
        console.log('[OnboardingGate] onboardingComplete:', onboardingComplete);

        // If on /onboarding and already complete, go to dashboard
        if (pathname === '/onboarding' && onboardingComplete) {
          console.log('[OnboardingGate] On /onboarding and complete, redirecting to dashboard');
          window.location.href = '/dashboard';
          return;
        }

        // If on protected route and not complete, go to onboarding
        if (isProtectedRoute && !onboardingComplete) {
          console.log('[OnboardingGate] Protected route but not complete, redirecting to /onboarding');
          window.location.href = '/onboarding';
          return;
        }

        console.log('[OnboardingGate] No redirect needed');
      } catch (err) {
        console.error('[OnboardingGate] Unexpected error:', err);
        // Don't block on error — let user retry
      }
    };

    checkOnboarding();
  }, [pathname]);

  return null;
}
