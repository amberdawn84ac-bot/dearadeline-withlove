'use client';

import { useEffect } from 'react';
import { usePathname } from 'next/navigation';

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
        const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') || '' : '';

        // Unauthenticated users should go to login
        if (!token) {
          if (pathname !== '/login') {
            window.location.href = '/login';
          }
          return;
        }

        // Add cache-busting to prevent stale reads after onboarding completion
        const cacheBuster = Date.now();
        console.log('[OnboardingGate] Checking status for pathname:', pathname, 'cacheBuster:', cacheBuster);
        const response = await fetch(`/brain/api/onboarding?_=${cacheBuster}`, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
          },
        });

        if (response.status === 401) {
          // Not authenticated, go to login
          console.log('[OnboardingGate] 401, redirecting to login');
          window.location.href = '/login';
          return;
        }

        if (!response.ok) {
          // Error fetching profile, log but don't block (user can retry)
          console.error('[OnboardingGate] Error checking onboarding status:', response.status, response.statusText);
          return;
        }

        const data = await response.json();
        const userProfile = data.user;
        let onboardingComplete = userProfile.onboardingComplete;
        console.log('[OnboardingGate] onboardingComplete:', onboardingComplete, 'pathname:', pathname);

        // Check if we recently completed onboarding (handles DB replication lag)
        // The onboarding page sets this flag after successful POST
        const justCompleted = localStorage.getItem('onboarding_just_completed');
        if (justCompleted && !onboardingComplete) {
          const timestamp = parseInt(justCompleted, 10);
          const secondsSince = (Date.now() - timestamp) / 1000;
          if (secondsSince < 60) {
            console.log('[OnboardingGate] Trusting local flag, onboarding completed', secondsSince, 'seconds ago');
            onboardingComplete = true;
          } else {
            localStorage.removeItem('onboarding_just_completed');
          }
        }

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
        console.error('Error in onboarding gate:', err);
        // Don't block on error — let user retry
      }
    };

    checkOnboarding();
  }, [pathname]);

  return null;
}
