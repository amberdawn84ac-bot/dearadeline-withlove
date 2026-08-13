'use client';

import { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';
import { getFamilyDashboard } from '@/lib/parent-client';
import ResourceVaultPage from '../../resource-vault/page';

export default function ParentResourceVaultPage() {
  const [access, setAccess] = useState<'checking' | 'allowed' | 'denied'>('checking');

  useEffect(() => {
    getFamilyDashboard()
      .then(() => setAccess('allowed'))
      .catch(() => setAccess('denied'));
  }, []);

  if (access === 'checking') {
    return (
      <div className="flex min-h-[60vh] items-center justify-center bg-[#FFFEF7]">
        <div className="text-center">
          <Loader2 className="mx-auto mb-3 h-6 w-6 animate-spin text-[#BD6809]" />
          <p className="text-sm text-[#2F4731]/60">Opening the parent source room…</p>
        </div>
      </div>
    );
  }

  if (access === 'denied') {
    return (
      <div className="flex min-h-[60vh] items-center justify-center bg-[#FFFEF7] px-6">
        <div className="max-w-md rounded-2xl border-2 border-[#E7DAC3] bg-white p-6 text-center">
          <h1 className="text-xl font-bold text-[#2F4731]">Parent access required</h1>
          <p className="mt-2 text-sm text-[#2F4731]/60">
            Adeline selects resources for students inside their lessons and learning plans. The full source catalog is available only from a parent account.
          </p>
        </div>
      </div>
    );
  }

  return <ResourceVaultPage />;
}
