'use client';

import { useEffect, useMemo, useState } from 'react';
import { Check, Copy, Mail, Users } from 'lucide-react';

interface FamilyIdentity {
  linkCode: string;
  parentId: string | null;
  parentDisplayName: string | null;
}

export function FamilyConnection() {
  const [family, setFamily] = useState<FamilyIdentity | null>(null);
  const [copied, setCopied] = useState<'code' | 'link' | null>(null);

  useEffect(() => {
    fetch('/api/student-auth', { cache: 'no-store' })
      .then(async response => response.ok ? response.json() : null)
      .then(data => {
        if (!data?.user) return;
        setFamily({
          linkCode: data.user.linkCode ?? data.user.link_code ?? '',
          parentId: data.user.parentId ?? data.user.parent_id ?? null,
          parentDisplayName: data.user.parentDisplayName ?? data.user.parent_display_name ?? null,
        });
      })
      .catch(() => undefined);
  }, []);

  const invitationUrl = useMemo(() => {
    if (!family?.linkCode || typeof window === 'undefined') return '';
    return `${window.location.origin}/login?parent=1&mode=register&invite=${encodeURIComponent(family.linkCode)}`;
  }, [family?.linkCode]);

  async function copy(value: string, kind: 'code' | 'link') {
    await navigator.clipboard.writeText(value);
    setCopied(kind);
    window.setTimeout(() => setCopied(null), 1800);
  }

  if (!family) return null;

  return (
    <section className="rounded-2xl border-2 border-[#E7DAC3] bg-white p-6">
      <div className="mb-3 flex items-center gap-3">
        <span className="grid h-10 w-10 place-items-center rounded-full bg-[#edf4ea] text-[#2F4731]"><Users size={20} /></span>
        <div>
          <h2 className="font-bold text-[#2F4731]">Family connection</h2>
          <p className="text-sm text-[#2F4731]/65">Connect this learning record to a parent dashboard.</p>
        </div>
      </div>

      {family.parentId ? (
        <div className="flex items-center gap-2 rounded-xl bg-[#edf4ea] px-4 py-3 text-sm font-semibold text-[#2F4731]">
          <Check size={18} /> Connected to {family.parentDisplayName || 'your parent or guardian'}
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-sm text-[#2F4731]/75">Your parent can create or sign in to their own account from this invitation. Your lessons, mastery, portfolio, and credits stay with this profile.</p>
          <div className="flex items-center gap-2 rounded-xl bg-[#f8f1e4] px-4 py-3">
            <code className="min-w-0 flex-1 truncate text-base font-black tracking-[.16em] text-[#2F4731]">{family.linkCode}</code>
            <button type="button" onClick={() => copy(family.linkCode, 'code')} className="rounded-lg p-2 text-[#2F4731] hover:bg-white" aria-label="Copy family code">
              {copied === 'code' ? <Check size={18} /> : <Copy size={18} />}
            </button>
          </div>
          <button type="button" onClick={() => copy(invitationUrl, 'link')} className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#2F4731] px-4 py-3 font-bold text-white hover:bg-[#3f6044]">
            {copied === 'link' ? <Check size={18} /> : <Mail size={18} />}
            {copied === 'link' ? 'Invitation copied' : 'Copy parent invitation'}
          </button>
        </div>
      )}
    </section>
  );
}
