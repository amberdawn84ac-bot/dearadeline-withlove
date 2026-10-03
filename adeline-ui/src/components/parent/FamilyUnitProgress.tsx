'use client';
import { useEffect, useState } from 'react';
import { advanceFamilyUnit, completeUnitExperience, CurrentUnit, getFamilyUnit } from '@/lib/curriculum-client';

export function FamilyUnitProgress({ householdId, onChange }: { householdId: string; onChange: () => void }) {
  const [unit, setUnit] = useState<CurrentUnit | null>(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  useEffect(() => { getFamilyUnit(householdId).then(data => setUnit(data.current)).catch(() => setError('Could not load unit progress.')); }, [householdId]);
  async function finish() {
    if (!unit) return;
    setBusy(true); setError('');
    try {
      if (unit.experienceId) await completeUnitExperience(householdId, unit.id, unit.experienceId);
      else await advanceFamilyUnit(householdId, unit.id);
      const data = await getFamilyUnit(householdId); setUnit(data.current); onChange();
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not update unit progress.'); }
    finally { setBusy(false); }
  }
  if (!unit && !error) return null;
  return <div className="mt-4 rounded-xl border border-[#D4C3A7] p-4">
    {unit && <><p className="font-bold">{unit.title}</p><p className="mt-1 text-sm">{unit.canonicalTopic ?? 'Every experience is complete. Ready for the next unit.'}</p>
      <button type="button" disabled={busy} onClick={() => void finish()} className="mt-3 rounded-lg bg-[#2F4731] px-3 py-2 text-sm text-white disabled:opacity-40">{busy ? 'Saving…' : unit.experienceId ? 'Mark family experience complete' : 'Advance to next unit'}</button>
      <p className="mt-2 text-xs">Completion records progress. Demonstrated evidence determines mastery.</p></>}
    {error && <p role="alert" className="mt-2 text-sm text-red-700">{error}</p>}
  </div>;
}
