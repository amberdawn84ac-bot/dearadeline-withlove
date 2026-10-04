'use client';
import { useState } from 'react';
import { enqueueFamilyUnit } from '@/lib/curriculum-client';

export function FamilyUnitComposer({householdId,tracks,onChange}:{householdId:string;tracks:Record<string,string>;onChange:()=>void}) {
  const [title,setTitle]=useState('');
  const [experiences,setExperiences]=useState([{id:'first',topic:'',track:'CREATION_SCIENCE'}]);
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  async function save() {
    setBusy(true);setError('');
    try {
      await enqueueFamilyUnit(householdId,title.trim(),experiences.map(e=>({canonical_topic:e.topic.trim(),track:e.track})));
      setTitle('');setExperiences([{id:'first',topic:'',track:'CREATION_SCIENCE'}]);onChange();
    } catch {setError('Could not queue this unit. Your plan is still here; try again.');}
    finally {setBusy(false);}
  }
  return <div className="mt-4 space-y-3 border-t border-[#E7DAC3] pt-4">
    <h3 className="font-bold">Plan a unit</h3>
    <label className="grid gap-1 text-sm">Unit title<input value={title} onChange={e=>setTitle(e.target.value)} maxLength={200} className="rounded-lg border p-2" placeholder="The Farm" /></label>
    <ol className="space-y-3">{experiences.map((experience,index)=><li key={experience.id} className="grid gap-2 rounded-xl border p-3">
      <label className="grid gap-1 text-sm">Experience {index+1}<input value={experience.topic} onChange={e=>setExperiences(previous=>previous.map(item=>item.id===experience.id?{...item,topic:e.target.value}:item))} maxLength={500} className="rounded-lg border p-2" placeholder="What does this soil need?" /></label>
      <label className="grid gap-1 text-sm">Primary area<select value={experience.track} onChange={e=>setExperiences(previous=>previous.map(item=>item.id===experience.id?{...item,track:e.target.value}:item))} className="rounded-lg border p-2">{Object.entries(tracks).map(([value,label])=><option key={value} value={value}>{label}</option>)}</select></label>
      {experiences.length>1&&<button type="button" onClick={()=>setExperiences(previous=>previous.filter(item=>item.id!==experience.id))} className="justify-self-start text-sm underline">Remove experience</button>}
    </li>)}</ol>
    <div className="flex gap-3"><button type="button" disabled={experiences.length>=50} onClick={()=>setExperiences(previous=>[...previous,{id:crypto.randomUUID(),topic:'',track:'CREATION_SCIENCE'}])} className="rounded-lg border px-3 py-2 text-sm">Add experience</button>
    <button type="button" disabled={busy||!title.trim()||experiences.some(e=>!e.topic.trim())} onClick={()=>void save()} className="rounded-lg bg-[#2F4731] px-3 py-2 text-sm text-white disabled:opacity-40">{busy?'Queuing…':'Queue unit'}</button></div>
    {error&&<p role="alert" className="text-sm text-red-700">{error}</p>}
  </div>;
}
