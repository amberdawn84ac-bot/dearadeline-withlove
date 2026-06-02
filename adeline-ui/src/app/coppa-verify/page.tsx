'use client';

import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { CheckCircle, XCircle, Loader2 } from 'lucide-react';
import { Suspense } from 'react';

function CoppaVerifyContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get('token');

  const [status, setStatus] = useState<'loading' | 'success' | 'expired' | 'error'>('loading');

  useEffect(() => {
    if (!token) {
      setStatus('error');
      return;
    }

    fetch(`/api/coppa?token=${encodeURIComponent(token)}`)
      .then(async (res) => {
        if (res.ok) {
          setStatus('success');
        } else if (res.status === 410) {
          setStatus('expired');
        } else {
          setStatus('error');
        }
      })
      .catch(() => setStatus('error'));
  }, [token]);

  if (status === 'loading') {
    return (
      <div className="flex flex-col items-center gap-4 text-[#2F4731]">
        <Loader2 className="w-12 h-12 animate-spin text-[#BD6809]" />
        <p className="text-lg font-medium">Verifying your approval…</p>
      </div>
    );
  }

  if (status === 'success') {
    return (
      <div className="text-center space-y-4">
        <CheckCircle className="w-16 h-16 text-green-600 mx-auto" />
        <h1
          className="text-3xl font-bold text-[#2F4731]"
          style={{ fontFamily: 'var(--font-emilys-candy), cursive' }}
        >
          Account Approved!
        </h1>
        <p className="text-[#2F4731]/70 leading-relaxed">
          Your child's Adeline account is now active. They can log in and start learning.
        </p>
        <p className="text-sm text-[#2F4731]/50">
          Thank you for helping them learn with purpose.
        </p>
      </div>
    );
  }

  if (status === 'expired') {
    return (
      <div className="text-center space-y-4">
        <XCircle className="w-16 h-16 text-amber-500 mx-auto" />
        <h1 className="text-2xl font-bold text-[#2F4731]">Link Expired</h1>
        <p className="text-[#2F4731]/70 leading-relaxed">
          This verification link has expired (links are valid for 72 hours).
          Your child can request a new one from the verification pending page.
        </p>
      </div>
    );
  }

  return (
    <div className="text-center space-y-4">
      <XCircle className="w-16 h-16 text-red-500 mx-auto" />
      <h1 className="text-2xl font-bold text-[#2F4731]">Something Went Wrong</h1>
      <p className="text-[#2F4731]/70">
        This link may have already been used, or it may be invalid.
        If you believe this is an error, please contact support.
      </p>
    </div>
  );
}

export default function CoppaVerifyPage() {
  return (
    <div className="min-h-screen bg-[#FFFEF7] flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-white border-2 border-[#E7DAC3] rounded-3xl p-10 shadow-lg">
        <Suspense fallback={
          <div className="flex justify-center">
            <Loader2 className="w-12 h-12 animate-spin text-[#BD6809]" />
          </div>
        }>
          <CoppaVerifyContent />
        </Suspense>
      </div>
    </div>
  );
}
