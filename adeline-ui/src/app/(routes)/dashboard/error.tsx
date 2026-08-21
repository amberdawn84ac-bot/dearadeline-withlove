'use client';

import { useEffect } from 'react';

export default function DashboardError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error(JSON.stringify({ level: 'error', message: 'dashboard_render_failed', digest: error.digest, error: error.message }));
  }, [error]);

  return (
    <div className="mx-auto mt-16 max-w-lg rounded-2xl border border-[#E7DAC3] bg-white p-8 text-center text-[#2F4731]">
      <h1 className="text-2xl font-bold">This page hit a snag.</h1>
      <p className="mt-3 text-sm text-[#2F4731]/70">Your learning record is safe. Try loading this part again.</p>
      <button type="button" onClick={reset} className="mt-5 rounded-xl bg-[#2F4731] px-5 py-3 font-bold text-white">Try again</button>
    </div>
  );
}
