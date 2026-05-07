'use client';

import { useState, useEffect } from 'react';
import { Loader2, AlertCircle } from 'lucide-react';
import { WelcomeFlow } from '@/components/onboarding/WelcomeFlow';
import { supabase } from '@/lib/supabase';

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
        // Get live session from Supabase
        const { data: sessionData, error: sessionError } = await supabase.auth.getSession();
        if (sessionError || !sessionData.session) {
          console.log('[OnboardingPage] No session, redirecting to login');
          window.location.href = '/login';
          return;
        }

        const token = sessionData.session.access_token;

        // Fetch current user profile to check onboarding status
        const cacheBuster = Date.now();
        const response = await fetch(`/brain/api/onboarding?_=${cacheBuster}`, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
          },
        });

        console.log('[OnboardingPage] GET /brain/api/onboarding status:', response.status);

        if (response.status === 401) {
          console.log('[OnboardingPage] 401 Unauthorized, redirecting to login');
          window.location.href = '/login';
          return;
        }

        if (response.status === 404) {
          // New user — no profile yet, show the onboarding form
          console.log('[OnboardingPage] 404 No profile, showing onboarding form');
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

        if (userProfile.onboardingComplete) {
          console.log('[OnboardingPage] Already complete, redirecting to dashboard');
          setStatus('redirecting');
          window.location.href = '/dashboard';
          return;
        }

        // Onboarding not complete, show the form
        setStatus('onboarding');
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to check onboarding status';
        console.error('[OnboardingPage] Error:', message);
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
      const { data: sessionData, error: sessionError } = await supabase.auth.getSession();
      if (sessionError || !sessionData.session) {
        throw new Error('Not authenticated - please log in again');
      }
      const token = sessionData.session.access_token;

      // Get invite code from URL query params
      const inviteCode = typeof window !== 'undefined'
        ? new URLSearchParams(window.location.search).get('invite') || undefined
        : undefined;

      console.log('[OnboardingPage] POST /brain/api/onboarding - submitting...');
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
        } catch {}
        throw new Error(detail);
      }

      const responseData = await response.json();
      if (!responseData?.user?.onboardingComplete) {
        throw new Error('Onboarding completed but response missing confirmation');
      }

      console.log('[OnboardingPage] POST successful - now verifying DB propagation...');

      // PRODUCTION FIX: Poll until GET confirms the flag is truly visible
      let attempts = 0;
      const maxAttempts = 12; // ~6 seconds max
      while (attempts < maxAttempts) {
        attempts++;
        const cacheBuster = Date.now();
        const checkRes = await fetch(`/brain/api/onboarding?_=${cacheBuster}`, {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
          },
        });

        if (checkRes.ok) {
          const checkData = await checkRes.json();
          if (checkData.user?.onboardingComplete === true) {
            console.log('[OnboardingPage] DB confirmed onboardingComplete=true');
            setStatus('redirecting');
            window.location.href = '/dashboard';
            return;
          }
        }
        await new Promise(resolve => setTimeout(resolve, 500));
      }

      console.warn('[OnboardingPage] Polling timed out - redirecting anyway');
      setStatus('redirecting');
      window.location.href = '/dashboard';
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to save onboarding profile';
      console.error('[OnboardingPage] Error:', message);
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
