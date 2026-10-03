'use client';
import {useState} from 'react';
import {EvidenceAttempt,saveTimelineCard} from '@/lib/curriculum-client';

export function TimelineCardEditor({studentId,attempts}:{studentId:string;attempts:EvidenceAttempt[]}) {
  const [selected,setSelected]=useState('');const [date,setDate]=useState('');const [claim,setClaim]=useState('');const [source,setSource]=useState('');const [missing,setMissing]=useState('');const [uncertainty,setUncertainty]=useState('');const [busy,setBusy]=useState(false);const [message,setMessage]=useState('');
  const attempt=attempts.find(a=>a.id===selected);
  async function save(){if(!attempt)return;setBusy(true);setMessage('');try{await saveTimelineCard(studentId,attempt,{date_start:date.trim(),claim:claim.trim(),sources:[{url:source.trim()}],omitted_perspectives:missing.split(',').map(s=>s.trim()).filter(Boolean),uncertainty:uncertainty.trim()});setMessage('Timeline card saved. Reopen the family timeline to see it.');}catch{setMessage('Could not save this card. Try again.');}finally{setBusy(false);}}
  if(!attempts.length)return null;
  return <details className="mt-4 text-sm"><summary className="cursor-pointer font-bold">Add a sourced timeline card</summary>
    <label className="mt-2 grid gap-1">Related work<select value={selected} onChange={e=>setSelected(e.target.value)} className="rounded-lg border p-2"><option value="">Choose evidence</option>{attempts.map(a=><option key={a.id} value={a.id}>{a.lessonId} · {a.kind}</option>)}</select></label>
    <label className="mt-2 grid gap-1">Historical date or year<input value={date} onChange={e=>setDate(e.target.value)} placeholder="1921 or -500 for 500 BCE" className="rounded-lg border p-2" /></label>
    <label className="mt-2 grid gap-1">Claim<textarea value={claim} onChange={e=>setClaim(e.target.value)} className="rounded-lg border p-2" /></label>
    <label className="mt-2 grid gap-1">Source URL<input type="url" value={source} onChange={e=>setSource(e.target.value)} className="rounded-lg border p-2" /></label>
    <label className="mt-2 grid gap-1">Perspectives missing from the record<input value={missing} onChange={e=>setMissing(e.target.value)} className="rounded-lg border p-2" /></label>
    <label className="mt-2 grid gap-1">What remains uncertain?<textarea value={uncertainty} onChange={e=>setUncertainty(e.target.value)} className="rounded-lg border p-2" /></label>
    <button type="button" onClick={()=>void save()} disabled={busy||!attempt||!date.trim()||!claim.trim()||!/^https?:\/\//.test(source)} className="mt-2 rounded-lg bg-[#2F4731] px-3 py-2 text-white disabled:opacity-40">{busy?'Saving…':'Save timeline card'}</button>
    {message&&<p role="status" className="mt-2">{message}</p>}
  </details>;
}
