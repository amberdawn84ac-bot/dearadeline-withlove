'use client';

import { useEffect, useState } from 'react';
import { Mail, RefreshCw, LogOut } from 'lucide-react';
import { supabase } from '@/lib/supabase';

export default function CoppaPendingPage() {
  const [resending, setResending] = useState(false);
  const [resent, setResent]       = useState(false);
  const [error, setError]         = useState('');

  // Periodically check if parent has verified
  useEffect(() => {
    const interval = setInterval(async () => {
      const { data: session } = await supabase.auth.getSession();
      if (!session.session?.access_token) return;

      const res = await fetch('/brain/api/onboarding', {
        headers: { Authorization: `Bearer ${session.session.access_token}` },
      });
      if (!res.ok) return;

      const data = await res.json() as { user?: { coppaVerified?: boolean } };
      if (data.user?.coppaVerified) {
        window.location.href = '/dashboard';
      }
    }, 10_000); // check every 10 seconds

    return () => clearInterval(interval);
  }, []);

  const handleResend = async () => {
    setResending(true);
    setError('');
    try {
      const { data: session } = await supabase.auth.getSession();
      if (!session.session?.access_token) throw new Error('Not logged in');

      const profileRes = await fetch('/brain/api/onboarding', {
        headers: { Authorization: `Bearer ${session.session.access_token}` },
      });
      const profile = await profileRes.json() as {
        user?: { id: string; name: string; parentName?: string; parentEmail?: string };
      };

      if (!profile.user?.parentEmail) {
        throw new Error('No parent email on file');
      }

      const res = await fetch('/api/coppa', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${session.session.access_token}`,
        },
        body: JSON.stringify({
          studentId:   profile.user.id,
          studentName: profile.user.name,
          parentName:  profile.user.parentName ?? 'Parent',
          parentEmail: profile.user.parentEmail,
        }),
      });

      if (!res.ok) throw new Error('Failed to resend');
      setResent(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Something went wrong');
    } finally {
      setResending(false);
    }
  };

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    window.location.href = '/login';
  };

  return (
    <div className="min-h-screen bg-[#FFFEF7] flex items-center justify-center p-4">
      <div className="w-full max-w-md text-center space-y-6">
        {/* Icon */}
        <div className="flex justify-center">
          <div className="w-20 h-20 bg-[#E7DAC3] rounded-full flex items-center justify-center">
            <Mail className="w-10 h-10 text-[#BD6809]" />
          </div>
        </div>

        {/* Heading */}
        <div>
          <h1
            className="text-3xl font-bold text-[#2F4731] mb-2"
            style={{ fontFamily: 'var(--font-emilys-candy), cursive' }}
          >
            Check Your Email
          </h1>
          <p className="text-[#2F4731]/70 leading-relaxed">
            We sent a verification link to your parent or guardian. They need to click it
            before you can start learning with Adeline.
          </p>
        </div>

        {/* Status box */}
        <div className="bg-white border-2 border-[#E7DAC3] rounded-2xl p-6 space-y-3">
          <p className="text-sm text-[#2F4731]/70">
            This page will automatically update once your parent approves your account.
          </p>
          <div className="flex items-center justify-center gap-2 text-[#BD6809] text-sm font-medium">
            <RefreshCw className="w-4 h-4 animate-spin" />
            Waiting for approval…
          </div>
        </div>

        {/* Resend */}
        {resent ? (
          <p className="text-green-700 text-sm font-medium">Verification email resent!</p>
        ) : (
          <button
            onClick={handleResend}
            disabled={resending}
            className="text-sm text-[#BD6809] underline underline-offset-2 hover:text-[#2F4731] disabled:opacity-50 transition-colors"
          >
            {resending ? 'Sending…' : "Didn't receive it? Resend the email"}
          </button>
        )}

        {error && <p className="text-red-600 text-sm">{error}</p>}

        <button
          onClick={handleSignOut}
          className="flex items-center gap-2 mx-auto text-sm text-[#2F4731]/50 hover:text-[#2F4731] transition-colors"
        >
          <LogOut className="w-4 h-4" />
          Sign out
        </button>
      </div>
    </div>
  );
}
