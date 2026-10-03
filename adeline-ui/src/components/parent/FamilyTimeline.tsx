'use client';
import {useEffect,useState} from 'react';
import {getFamilyTimeline,TimelineCard} from '@/lib/curriculum-client';

export function FamilyTimeline({householdId}:{householdId:string}) {
  const [cards,setCards]=useState<TimelineCard[]>([]);const [error,setError]=useState('');
  useEffect(()=>{let active=true;getFamilyTimeline(householdId).then(data=>{if(active)setCards(data);}).catch(()=>{if(active)setError('Could not load the family timeline.');});return()=>{active=false;};},[householdId]);
  return <details className="rounded-2xl border border-[#DED1BD] bg-[#FFFDF7] p-5"><summary className="cursor-pointer font-bold">Family timeline</summary>
    <p className="mt-2 text-sm">Investigations can happen in any order. The record keeps their historical dates together.</p>
    {!cards.length&&!error&&<p className="mt-3 text-sm">Add a sourced timeline card from a child’s evidence record.</p>}
    <ol className="mt-3 space-y-3">{cards.map(card=><li key={card.id} className="rounded-xl border p-3"><p className="text-sm font-bold">{card.dateStart}{card.dateEnd&&`–${card.dateEnd}`} · {card.studentName}</p><p className="mt-2 text-sm">{card.claim}</p>
      {card.sources.filter(source=>source.url&&/^https?:\/\//.test(source.url)).map((source,index)=><a key={`${card.id}-${index}`} href={source.url} target="_blank" rel="noreferrer" className="mt-2 mr-3 inline-block text-sm underline">Source {index+1}</a>)}
      {card.omittedPerspectives.length>0&&<p className="mt-2 text-sm">Missing perspectives: {card.omittedPerspectives.join(', ')}</p>}
      {card.uncertainty&&<p className="mt-2 text-sm">Uncertainty: {card.uncertainty}</p>}
    </li>)}</ol>{error&&<p role="alert" className="mt-2 text-sm">{error}</p>}
  </details>;
}
