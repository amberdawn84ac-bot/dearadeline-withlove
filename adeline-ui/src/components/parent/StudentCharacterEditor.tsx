'use client';
import { useEffect, useState } from 'react';
import { getStudentCharacter, saveStudentCharacter } from '@/lib/curriculum-client';

export function StudentCharacterEditor({ studentId }: { studentId: string }) {
  const [name, setName] = useState('');
  const [identity, setIdentity] = useState('');
  const [roles, setRoles] = useState('');
  const [traits, setTraits] = useState<string[]>([]);
  const [visualData, setVisualData] = useState<Record<string, unknown>>({});
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    let active = true; setReady(false);
    getStudentCharacter(studentId).then(character => {
      if (!active) return;
      setName(character?.name ?? ''); setIdentity(character?.identity ?? '');
      const preferences = character?.rolePreferences ?? [];
      setRoles((typeof preferences === 'string' ? JSON.parse(preferences) as string[] : preferences).join(', ')); setTraits(typeof character?.persistentTraits === "string" ? JSON.parse(character.persistentTraits) as string[] : character?.persistentTraits ?? []); setVisualData(character?.visualData ?? {}); setReady(true);
    }).catch(() => { if (active) setMessage('Could not load the character. Try opening this child again.'); });
    return () => { active = false; };
  }, [studentId]);
  async function save() {
    setBusy(true); setMessage('');
    try {
      // Only edit these fields; existing traits and appearance are retained server-side.
      await saveStudentCharacter(studentId, {name,identity,role_preferences:roles.split(',').map(r=>r.trim()).filter(Boolean),persistent_traits:traits,visual_data:visualData});
      setMessage('Character saved. It will be used when the next experience opens.');
    } catch { setMessage('Could not save the character. Try again.'); }
    finally { setBusy(false); }
  }
  return <section className="rounded-2xl border border-[#DED1BD] p-5">
    <h3 className="font-bold">Learning character</h3>
    <p className="mt-2 text-sm">Choose a lasting identity and preferred responsibilities for participating in family work.</p>
    <label className="mt-3 grid gap-1 text-sm">Name<input value={name} onChange={e=>setName(e.target.value)} maxLength={100} className="rounded-lg border p-2" /></label>
    <label className="mt-3 grid gap-1 text-sm">Identity<textarea value={identity} onChange={e=>setIdentity(e.target.value)} maxLength={2000} className="rounded-lg border p-2" /></label>
    <label className="mt-3 grid gap-1 text-sm">Preferred roles, separated by commas<input value={roles} onChange={e=>setRoles(e.target.value)} className="rounded-lg border p-2" placeholder="Observer, builder, investigator" /></label>
    <button type="button" onClick={()=>void save()} disabled={!ready || busy || !name.trim()} className="mt-3 rounded-lg bg-[#2F4731] px-3 py-2 text-sm text-white disabled:opacity-40">{busy?'Saving…':'Save character'}</button>
    {message && <p role="status" className="mt-2 text-sm">{message}</p>}
  </section>;
}
