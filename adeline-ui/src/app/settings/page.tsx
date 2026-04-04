'use client';

import { useState, useEffect } from 'react';
import { Loader2, AlertCircle } from 'lucide-react';
import { SettingsForm } from '@/components/settings/SettingsForm';

interface UserProfile {
  id: string;
  name: string;
  gradeLevel: string;
  mathLevel?: number;
  elaLevel?: number;
  scienceLevel?: number;
  historyLevel?: number;
  interests: string[];
  learningStyle?: string;
  pacingMultiplier: number;
  state?: string;
  targetGraduationYear?: number;
  onboardingComplete: boolean;
}

export default function SettingsPage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [status, setStatus] = useState<'loading' | 'ready' | 'error' | 'not-onboarded'>('loading');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') || '' : '';

        const response = await fetch('/api/onboarding', {
          method: 'GET',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        });

        if (response.status === 401) {
          window.location.href = '/login';
          return;
        }

        if (!response.ok) {
          throw new Error('Failed to load profile');
        }

        const data = await response.json();
        const userProfile: UserProfile = data.user;

        // If onboarding is not complete, redirect to onboarding
        if (!userProfile.onboardingComplete) {
          setStatus('not-onboarded');
          return;
        }

        setProfile(userProfile);
        setStatus('ready');
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Failed to load profile';
        setError(message);
        setStatus('error');
      }
    };

    fetchProfile();
  }, []);

  const handleRetry = () => {
    setError(null);
    setStatus('loading');
    window.location.reload();
  };

  // Loading state
  if (status === 'loading') {
    return (
      <div className="flex items-center justify-center h-screen bg-[#FFFEF7]">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-8 h-8 animate-spin text-[#BD6809]" />
          <p className="text-[#2F4731] text-lg font-semibold">Loading settings…</p>
        </div>
      </div>
    );
  }

  // Not onboarded — redirect to onboarding
  if (status === 'not-onboarded') {
    return (
      <div className="flex items-center justify-center h-screen bg-[#FFFEF7]">
        <div className="max-w-md w-full mx-auto px-6">
          <div className="bg-white rounded-2xl border-2 border-[#E7DAC3] p-8 text-center">
            <h2 className="text-xl font-bold text-[#2F4731] mb-2">Onboarding Required</h2>
            <p className="text-[#2F4731]/70 text-sm mb-6">
              Please complete onboarding first before accessing settings.
            </p>
            <button
              onClick={() => {
                window.location.href = '/onboarding';
              }}
              className="w-full px-4 py-2 bg-[#BD6809] text-white rounded-lg font-semibold hover:bg-[#A55708] transition-colors"
            >
              Go to Onboarding
            </button>
          </div>
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

  // Settings form
  if (status === 'ready' && profile) {
    return (
      <div className="flex h-screen bg-[#FFFEF7]">
        {/* Main content */}
        <div className="flex-1 overflow-y-auto">
          {/* Header */}
          <header className="bg-white border-b-2 border-[#E7DAC3] px-6 py-5 sticky top-0 z-10">
            <h1 className="text-2xl font-bold text-[#2F4731]" style={{ fontFamily: 'var(--font-emilys-candy), cursive' }}>
              Settings
            </h1>
            <p className="text-[#2F4731]/60 mt-0.5 text-sm">Manage your learning preferences and profile</p>
          </header>

          {/* Content */}
          <main className="px-6 py-8 max-w-5xl">
            <SettingsForm initialProfile={profile} />
          </main>
        </div>
      </div>
    );
  }

  return null;
}
