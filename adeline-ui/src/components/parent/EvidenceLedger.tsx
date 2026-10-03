'use client';
import { TimelineCardEditor } from "@/components/parent/TimelineCardEditor";
import { useEffect, useState } from 'react';
import { EvidenceAttempt, evaluateEvidence, getEvidencePortfolio } from '@/lib/curriculum-client';

function EvidenceReview({studentId,attempt}:{studentId:string;attempt:EvidenceAttempt}) {
  const [skill,setSkill]=useState('');const [reasoning,setReasoning]=useState('');
  const [result,setResult]=useState<'developing'|'demonstrated'|'secure'>('developing');
  const [busy,setBusy]=useState(false);const [message,setMessage]=useState('');
  async function review() {
    setBusy(true);setMessage('');
    try {await evaluateEvidence(studentId,attempt.id,skill.trim(),result,reasoning.trim());setMessage('Evidence reviewed.');}
    catch {setMessage('Could not save this review. Try again.');}finally {setBusy(false);}
  }
  return <details className="mt-3 text-sm"><summary className="cursor-pointer font-bold">Review demonstrated learning</summary>
    <label className="mt-2 grid gap-1">Skill or standard demonstrated<input value={skill} onChange={e=>setSkill(e.target.value)} className="rounded-lg border p-2" /></label>
    <label className="mt-2 grid gap-1">Finding<select value={result} onChange={e=>setResult(e.target.value as typeof result)} className="rounded-lg border p-2"><option value="developing">Developing</option><option value="demonstrated">Demonstrated</option><option value="secure">Secure</option></select></label>
    <label className="mt-2 grid gap-1">What evidence supports your finding?<textarea value={reasoning} onChange={e=>setReasoning(e.target.value)} className="rounded-lg border p-2" /></label>
    <button type="button" disabled={busy||!skill.trim()||!reasoning.trim()} onClick={()=>void review()} className="mt-2 rounded-lg bg-[#2F4731] px-3 py-2 text-white disabled:opacity-40">{busy?'Saving…':'Save review'}</button>
    {message&&<p role="status" className="mt-2">{message}</p>}
  </details>;
}

export function EvidenceLedger({ studentId }: { studentId: string }) {
  const [attempts, setAttempts] = useState<EvidenceAttempt[]>([]);
  const [error, setError] = useState('');
  useEffect(() => {
    let active = true;
    getEvidencePortfolio(studentId).then(data => { if (active) setAttempts(data.attempts); }).catch(() => { if (active) setError('Could not load evidence.'); });
    return () => { active = false; };
  }, [studentId]);
  return <section className="rounded-2xl border border-[#DED1BD] p-5">
    <h3 className="font-bold">Evidence and revisions</h3>
    <p className="mt-2 text-sm">Earlier attempts stay in the record as thinking changes.</p>
    {!attempts.length && !error && <p className="mt-3 text-sm">Saved notes, observations and reviewed work will appear here.</p>}
    <ol className="mt-3 space-y-3">{attempts.map(attempt => <li key={attempt.id} className="rounded-xl border p-3">
      <p className="text-xs font-bold capitalize">{attempt.kind.replaceAll('_',' ')} · {attempt.lessonId}{attempt.parentAttemptId ? ' · revised attempt' : ''}</p>
      {typeof attempt.content.text === 'string' && <p className="mt-2 whitespace-pre-wrap text-sm">{attempt.content.text}</p>}
      {typeof attempt.content.proficiency === 'string' && <p className="mt-2 text-sm">Review: {attempt.content.proficiency.toLowerCase()}</p>}
      {typeof attempt.content.claim === 'string' && <p className="mt-2 text-sm">{attempt.content.claim}</p>}
      <EvidenceReview studentId={studentId} attempt={attempt} />
    </li>)}</ol>
    <TimelineCardEditor studentId={studentId} attempts={attempts} />
    {error && <p role="alert" className="mt-2 text-sm">{error}</p>}
  </section>;
}
