'use client';

import { useState, useEffect } from 'react';
import { Loader2, AlertCircle } from 'lucide-react';
import { WelcomeFlow } from '@/components/onboarding/WelcomeFlow';

interface OnboardingPageProps {
  params?: Record<string, unknown>;
}

export default function OnboardingPage() {
  const [status, setStatus] = useState<'checking' | 'onboarding' | 'error' | 'redirecting'>('checking');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const checkOnboardingStatus = async () => {
      try {
        // Fetch current user profile to check onboarding status
        const response = await fetch('/api/onboarding', {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${typeof window !== 'undefined' ? localStorage.getItem('auth_token') || '' : ''}`,
            'Content-Type': 'application/json',
          },
        });

        if (response.status === 401) {
          // Not authenticated, redirect to login
          window.location.href = '/login';
          return;
        }

        if (!response.ok) {
          throw new Error(`Failed to check onboarding status: ${response.statusText}`);
        }

        const data = await response.json();
        const userProfile = data.user;

        // If onboarding is already complete, redirect to dashboard
        if (userProfile.onboardingComplete) {
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

  const handleOnboardingComplete = async (data: {
    name: string;
    gradeLevel: string;
    interests: string[];
    learningStyle: string;
    state: string;
    targetGraduationYear: number;
    coppaConsent: boolean;
  }) => {
    try {
      setStatus('redirecting');

      const response = await fetch('/api/onboarding', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${typeof window !== 'undefined' ? localStorage.getItem('auth_token') || '' : ''}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to save onboarding profile');
      }

      // Success — redirect to dashboard
      window.location.href = '/dashboard';
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to save onboarding profile';
      setError(message);
      setStatus('error');
    }
  };

  const handleRetry = () => {
    setError(null);
    setStatus('checking');
    window.location.reload();
  };

  // Loading state
  if (status === 'checking' || status === 'redirecting') {
    return (
      <div className="flex items-center justify-center h-screen bg-[#FFFEF7]">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 animate-spin text-[#BD6809]" />
          <p className="text-[#2F4731] text-lg font-semibold">Loading…</p>
        </div>
      </div>
    );
  }

  // Error state
  if (status === 'error') {
    return (
      <div className="flex items-center justify-center h-screen bg-[#FFFEF7]">
        <div className="max-w-md w-full mx-auto px-6">
          <div className="bg-white rounded-2xl border-2 border-[#E7DAC3] p-8">
            <div className="flex items-start gap-4 mb-4">
              <AlertCircle className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" />
              <div>
                <h2 className="text-lg font-bold text-[#2F4731] mb-2">Error</h2>
                <p className="text-[#2F4731]/70 text-sm mb-4">{error}</p>
              </div>
            </div>
            <button
              onClick={handleRetry}
              className="w-full px-4 py-2 bg-[#BD6809] text-white rounded-lg font-semibold hover:bg-[#A55708] transition-colors"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Onboarding form
  return (
    <div className="flex items-center justify-center h-screen bg-[#FFFEF7]">
      <WelcomeFlow onComplete={handleOnboardingComplete} />
    </div>
  );
}
