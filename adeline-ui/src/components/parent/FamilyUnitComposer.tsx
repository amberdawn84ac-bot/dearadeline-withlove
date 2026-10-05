'use client';
import { useState } from 'react';
import { enqueueFamilyUnit, planFamilyInvestigation, type InvestigationSequence } from '@/lib/curriculum-client';

export function FamilyUnitComposer({householdId,tracks,onChange}:{householdId:string;tracks:Record<string,string>;onChange:()=>void}) {
  const [title,setTitle]=useState('');
  const [experiences,setExperiences]=useState([{id:'first',topic:'',track:'CREATION_SCIENCE'}]);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const [sessionCount,setSessionCount]=useState(4);
  const [materials,setMaterials]=useState('');
  const [sequence,setSequence]=useState<InvestigationSequence|null>(null);
  async function generate() {
    setBusy(true);setError('');
    try {
      const plan=await planFamilyInvestigation(householdId,title.trim(),sessionCount,materials);
      setSequence(plan);setTitle(plan.title);
      setExperiences(plan.experiences.map((experience,index)=>({id:`generated-${index}`,topic:experience.canonical_topic,track:experience.track})));
    } catch {setError('Could not prepare the sessions. Your current plan is still here; try again.');}
    finally {setBusy(false);}
  }
  async function save() {
    setBusy(true);setError('');
    try {
      await enqueueFamilyUnit(householdId,title.trim(),experiences.map(e=>({canonical_topic:e.topic.trim(),track:e.track})));
      setTitle('');setExperiences([{id:'first',topic:'',track:'CREATION_SCIENCE'}]);setSequence(null);onChange();
    } catch {setError('Could not queue this unit. Your plan is still here; try again.');}
    finally {setBusy(false);}
  }
  return <div className="mt-4 space-y-3 border-t border-[#E7DAC3] pt-4">
    <h3 className="font-bold">Plan a unit</h3>
    <label className="grid gap-1 text-sm">Unit title<input value={title} onChange={e=>setTitle(e.target.value)} maxLength={200} className="rounded-lg border p-2" placeholder="The Farm" /></label>
    <div className="space-y-2 rounded-xl bg-[#E7EFE5] p-3">
      <label className="grid gap-1 text-sm">Number of sessions<input type="number" min={2} max={10} value={sessionCount} onChange={e=>setSessionCount(Number(e.target.value))} className="rounded-lg border p-2" /></label>
      <label className="grid gap-1 text-sm">Materials you have<textarea value={materials} onChange={e=>setMaterials(e.target.value)} maxLength={600} className="rounded-lg border p-2" placeholder="For example: jars, soil, measuring cups, magnifying glass" /></label>
      <button type="button" disabled={busy||!title.trim()||sessionCount<2||sessionCount>10} onClick={()=>void generate()} className="rounded-lg bg-[#2F4731] px-3 py-2 text-sm text-white disabled:opacity-40">{busy?'Preparing…':'Let Adeline plan the sessions'}</button>
      <p className="text-xs">Review and edit before queuing. A session may take several days; dates do not advance it.</p>
    </div>
    {sequence&&<aside className="space-y-2 rounded-xl border p-3"><p className="font-bold">{sequence.shared_question}</p><ol className="list-decimal space-y-2 pl-5">{sequence.sessions.map((session,index)=><li key={index} className="text-sm"><strong>{session.title}</strong><p>{session.objective}</p><p>Evidence: {session.evidence_required}</p><p>Useful resource: {session.resource_hint}</p></li>)}</ol><p className="text-xs">This is the generated outline. The editable experiences below are what will be queued.</p></aside>}
    <ol className="space-y-3">{experiences.map((experience,index)=><li key={experience.id} className="grid gap-2 rounded-xl border p-3">
      <label className="grid gap-1 text-sm">Experience {index+1}<input value={experience.topic} onChange={e=>setExperiences(previous=>previous.map(item=>item.id===experience.id?{...item,topic:e.target.value}:item))} maxLength={1000} className="rounded-lg border p-2" placeholder="What does this soil need?" /></label>
      <label className="grid gap-1 text-sm">Primary area<select value={experience.track} onChange={e=>setExperiences(previous=>previous.map(item=>item.id===experience.id?{...item,track:e.target.value}:item))} className="rounded-lg border p-2">{Object.entries(tracks).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>
      {experiences.length>1&&<button type="button" onClick={()=>setExperiences(previous=>previous.filter(item=>item.id!==experience.id))} className="justify-self-start text-sm underline">Remove experience</button>}
    </li>)}</ol>
    <div className="flex gap-3"><button type="button" disabled={experiences.length>=50} onClick={()=>setExperiences(previous=>[...previous,{id:crypto.randomUUID(),topic:'',track:'CREATION_SCIENCE'}])} className="rounded-lg border px-3 py-2 text-sm">Add experience</button>
    <button type="button" disabled={busy||!title.trim()||experiences.some(e=>!e.topic.trim())} onClick={()=>void save()} className="rounded-lg bg-[#2F4731] px-3 py-2 text-sm text-white disabled:opacity-40">{busy?'Queuing…':'Queue unit'}</button></div>
    {error&&<p role="alert" className="text-sm text-red-700">{error}</p>}
  </div>;
}
