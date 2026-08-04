'use client';

import { useState, FormEvent } from 'react';
import { claimStudent } from '@/lib/parent-client';

interface Props {
  onClose: () => void;
  onClaimed: () => void;
}

export function ClaimStudentDialog({ onClose, onClaimed }: Props) {
  const [code, setCode] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await claimStudent(code.trim().toUpperCase());
      onClaimed();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not link that code.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-6" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-xl p-6 max-w-sm w-full space-y-4" onClick={e => e.stopPropagation()}>
        <h3 className="text-lg font-bold text-[#2F4731]">Link a Mobile Kid</h3>
        <p className="text-sm text-[#2F4731]/70">
          Ask your kid to open Adelinemobile → Settings → "Link with a parent" for their 6-digit code.
        </p>
        <form onSubmit={handleSubmit} className="space-y-3">
          <input
            type="text"
            required
            value={code}
            onChange={e => setCode(e.target.value.toUpperCase().slice(0, 6))}
            maxLength={6}
            placeholder="A3F9C2"
            className="w-full px-4 py-3 border border-[#2F4731]/20 rounded-xl text-center font-mono text-xl tracking-widest focus:outline-none focus:border-[#BD6809]"
          />
          {error && <p className="text-sm text-red-600 bg-red-50 px-3 py-2 rounded-lg">{error}</p>}
          <div className="flex gap-3">
            <button type="button" onClick={onClose} className="flex-1 py-2.5 bg-gray-100 hover:bg-gray-200 rounded-xl font-semibold text-[#2F4731]">
              Cancel
            </button>
            <button type="submit" disabled={loading || code.length !== 6} className="flex-1 py-2.5 bg-[#2F4731] hover:bg-[#BD6809] disabled:opacity-50 text-white rounded-xl font-semibold">
              {loading ? 'Linking...' : 'Link'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
