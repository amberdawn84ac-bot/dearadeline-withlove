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

        const response = await fetch('/api/onboarding', {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        });

        if (response.status === 401) {
          // Not authenticated, go to login
          window.location.href = '/login';
          return;
        }

        if (!response.ok) {
          // Error fetching profile, log but don't block (user can retry)
          console.error('Error checking onboarding status:', response.statusText);
          return;
        }

        const data = await response.json();
        const userProfile = data.user;
        const onboardingComplete = userProfile.onboardingComplete;

        // If on /onboarding and already complete, go to dashboard
        if (pathname === '/onboarding' && onboardingComplete) {
          window.location.href = '/dashboard';
          return;
        }

        // If on protected route and not complete, go to onboarding
        if (isProtectedRoute && !onboardingComplete) {
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
