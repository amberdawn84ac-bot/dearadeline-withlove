'use client';

import { useState, useEffect } from 'react';
import { Loader2, AlertCircle } from 'lucide-react';
import { WelcomeFlow } from '@/components/onboarding/WelcomeFlow';

interface OnboardingPageProps {
  params?: Record<string, unknown>;
}

export default function OnboardingPage() {
  const [status, setStatus] = useState<'checking' | 'onboarding' | 'submitting' | 'error' | 'redirecting'>('checking');
  const [error, setError] = useState<string | null>(null);
  const [pendingData, setPendingData] = useState<Parameters<typeof handleOnboardingComplete>[0] | null>(null);

  useEffect(() => {
    const checkOnboardingStatus = async () => {
      try {
        // Fetch current user profile to check onboarding status
        // Add cache-busting to prevent stale reads
        const cacheBuster = Date.now();
        const response = await fetch(`/brain/api/onboarding?_=${cacheBuster}`, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${typeof window !== 'undefined' ? localStorage.getItem('auth_token') || '' : ''}`,
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
          },
        });

        if (response.status === 401) {
          // Not authenticated, redirect to login
          window.location.href = '/login';
          return;
        }

        if (response.status === 404) {
          // New user — no profile yet. Still respect the local flag in case
          // the DB hasn't propagated a recent successful POST yet.
          const justCompleted = localStorage.getItem('onboarding_just_completed');
          if (justCompleted && (Date.now() - parseInt(justCompleted, 10)) / 1000 < 60) {
            setStatus('redirecting');
            window.location.href = '/dashboard';
            return;
          }
          setStatus('onboarding');
          return;
        }

        if (!response.ok) {
          let detail = `Failed to check onboarding status: ${response.statusText}`;
          try {
            const body = await response.text();
            const parsed = JSON.parse(body);
            detail = parsed.detail || body;
          } catch { /* plain text */ }
          throw new Error(detail);
        }

        const data = await response.json();
        const userProfile = data.user;

        // Trust the local flag if DB is stale (handles read-after-write lag)
        let onboardingComplete = userProfile.onboardingComplete;
        if (!onboardingComplete) {
          const justCompleted = localStorage.getItem('onboarding_just_completed');
          if (justCompleted && (Date.now() - parseInt(justCompleted, 10)) / 1000 < 60) {
            onboardingComplete = true;
          }
        }

        if (onboardingComplete) {
          setStatus('redirecting');
          window.location.href = '/dashboard';
          return;
        }

        // Onboarding not complete, show the form
        setStatus('onboarding');
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to check onboarding status';
        setError(message);
        setStatus('error');
      }
    };

    checkOnboardingStatus();
  }, []);

  async function handleOnboardingComplete(data: {
    name: string;
    gradeLevel: string;
    interests: string[];
    learningStyle: string;
    state: string;
    targetGraduationYear: number;
    coppaConsent: boolean;
  }) {
    setPendingData(data);
    setError(null);
    setStatus('submitting');
    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') || '' : '';
      const inviteCode = typeof window !== 'undefined' ? localStorage.getItem('adeline_founder_code') || undefined : undefined;

      const response = await fetch('/brain/api/onboarding', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ ...data, ...(inviteCode ? { inviteCode } : {}) }),
      });

      if (!response.ok) {
        let detail = 'Failed to save onboarding profile';
        try {
          const body = await response.text();
          const parsed = JSON.parse(body);
          detail = parsed.detail || body;
        } catch {
          // body was plain text — use as-is if meaningful
        }

        // The profile may have been written in a prior attempt whose response
        // never reached the client (network drop, invite code race, etc.).
        // Check whether onboarding actually completed before showing an error.
        try {
          const profileCheck = await fetch(`/brain/api/onboarding?_=${Date.now()}`, {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Cache-Control': 'no-cache, no-store, must-revalidate',
            },
          });
          if (profileCheck.ok) {
            const profileData = await profileCheck.json();
            if (profileData?.user?.onboardingComplete) {
              localStorage.setItem('onboarding_just_completed', Date.now().toString());
              setStatus('redirecting');
              window.location.href = '/dashboard';
              return;
            }
          }
        } catch {
          // Profile check failed — fall through to show the original error
        }

        throw new Error(detail);
      }

      // Success — set local flag to handle DB replication lag, then wait for propagation
      localStorage.setItem('onboarding_just_completed', Date.now().toString());
      setStatus('redirecting');
      console.log('[Onboarding] POST successful, waiting 3s for DB propagation...');
      await new Promise((resolve) => setTimeout(resolve, 3000)); // 3s delay for read-after-write consistency
      console.log('[Onboarding] Redirecting to dashboard...');
      window.location.href = '/dashboard';
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to save onboarding profile';
      setError(message);
      setStatus('onboarding');
    }
  }

  const handleRetry = () => {
    if (pendingData) {
      handleOnboardingComplete(pendingData);
    } else {
      setError(null);
      setStatus('checking');
      window.location.reload();
    }
  };

  // Loading state
  if (status === 'checking' || status === 'redirecting' || status === 'submitting') {
    return (
      <div className="flex items-center justify-center h-screen bg-[#FFFEF7]">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 animate-spin text-[#BD6809]" />
          <p className="text-[#2F4731] text-lg font-semibold">Loading…</p>
        </div>
      </div>
    );
  }

  // Onboarding form (with optional inline error banner)
  return (
    <div className="flex flex-col items-center justify-center h-screen bg-[#FFFEF7]">
      {error && (
        <div className="w-full max-w-2xl px-4 mb-4">
          <div className="flex items-start gap-3 bg-red-50 border border-red-200 rounded-xl px-4 py-3">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm text-red-700 font-medium">{error}</p>
            </div>
            <button onClick={handleRetry} className="text-xs text-red-600 font-semibold underline whitespace-nowrap">
              Try Again
            </button>
          </div>
        </div>
      )}
      <WelcomeFlow onComplete={handleOnboardingComplete} />
    </div>
  );
}
