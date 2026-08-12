'use client';

import { useMemo, useState } from 'react';
import { ExternalLink, Search, ShieldCheck, BookOpen, Database, Map, Gamepad2, Microscope, Landmark, Sprout } from 'lucide-react';
import { OPEN_LEARNING_RESOURCES, RESOURCE_POLICY_LABELS, type ResourceKind } from '@/data/learningVault';

const KIND_LABELS: Record<ResourceKind, string> = {
  curriculum: 'Curriculum', game: 'Games', simulation: 'Interactives', primary_sources: 'Primary Sources',
  coding: 'Coding', reference: 'Reference', dataset: 'Real Data', map: 'Historical Maps',
  virtual_museum: 'Virtual Museums', citizen_science: 'Citizen Science',
};

const KIND_ICONS: Partial<Record<ResourceKind, typeof BookOpen>> = {
  curriculum: BookOpen, game: Gamepad2, coding: Gamepad2, simulation: Microscope,
  primary_sources: Landmark, dataset: Database, map: Map, virtual_museum: Landmark,
  citizen_science: Microscope, reference: Sprout,
};

export default function ResourceVaultPage() {
  const [query, setQuery] = useState('');
  const [kind, setKind] = useState<ResourceKind | 'all'>('all');
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return OPEN_LEARNING_RESOURCES.filter((resource) => {
      const matchesKind = kind === 'all' || resource.kind === kind;
      const haystack = [resource.title, resource.provider, resource.description, ...resource.subjects, ...resource.missionIdeas].join(' ').toLowerCase();
      return matchesKind && (!q || haystack.includes(q));
    });
  }, [query, kind]);

  return (
    <div className="min-h-screen bg-[#FFFEF7] pb-12">
      <div className="max-w-7xl mx-auto px-6 py-8">
        <div className="mb-8">
          <p className="text-xs font-black uppercase tracking-[0.22em] text-[#BD6809] mb-2">Adeline's source room</p>
          <h1 className="text-4xl md:text-5xl font-bold text-[#2F4731]" style={{ fontFamily: 'var(--font-emilys-candy), cursive' }}>
            Open Learning Vault
          </h1>
          <p className="max-w-3xl text-[#2F4731]/65 mt-3">
            Real primary sources, public data, museums, coding tools, simulations, open curriculum, and specialist homestead research for building missions. Free access never automatically means permission to copy.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-3 mb-7">
          <div className="rounded-2xl border border-[#E7DAC3] bg-white p-4"><p className="text-xs uppercase tracking-wider text-[#2F4731]/50">Sources</p><p className="text-2xl font-black text-[#2F4731]">{OPEN_LEARNING_RESOURCES.length}</p></div>
          <div className="rounded-2xl border border-[#E7DAC3] bg-white p-4"><p className="text-xs uppercase tracking-wider text-[#2F4731]/50">Open reuse</p><p className="text-2xl font-black text-[#2F4731]">{OPEN_LEARNING_RESOURCES.filter(r => r.policy === 'OPEN_REUSE').length}</p></div>
          <div className="rounded-2xl border border-[#E7DAC3] bg-white p-4"><p className="text-xs uppercase tracking-wider text-[#2F4731]/50">Rule</p><p className="font-bold text-[#2F4731]">Rights check before ingestion</p></div>
        </div>

        <div className="flex flex-col lg:flex-row gap-3 mb-6">
          <label className="flex-1 flex items-center gap-2 rounded-xl border-2 border-[#E7DAC3] bg-white px-4 py-3">
            <Search className="w-4 h-4 text-[#2F4731]/40" />
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search child labor, herbs, maps, astronomy, coding..." className="w-full outline-none bg-transparent text-sm text-[#2F4731]" />
          </label>
          <select value={kind} onChange={(e) => setKind(e.target.value as ResourceKind | 'all')} className="rounded-xl border-2 border-[#E7DAC3] bg-white px-4 py-3 text-sm text-[#2F4731]">
            <option value="all">All resource types</option>
            {Object.entries(KIND_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </div>

        <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map((resource) => {
            const Icon = KIND_ICONS[resource.kind] ?? BookOpen;
            const policy = RESOURCE_POLICY_LABELS[resource.policy];
            return (
              <article key={resource.id} className="rounded-2xl border-2 border-[#E7DAC3] bg-white p-5 flex flex-col hover:border-[#BD6809] hover:shadow-lg transition-all">
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 rounded-xl bg-[#2F4731]/8 flex items-center justify-center shrink-0"><Icon className="w-5 h-5 text-[#2F4731]" /></div>
                  <div className="min-w-0">
                    <p className="text-[10px] font-black uppercase tracking-wider text-[#BD6809]">{KIND_LABELS[resource.kind]}</p>
                    <h2 className="font-black text-[#2F4731] leading-tight">{resource.title}</h2>
                    <p className="text-xs text-[#2F4731]/50 mt-0.5">{resource.provider}</p>
                  </div>
                </div>
                <p className="text-sm text-[#2F4731]/65 mt-4">{resource.description}</p>
                <div className="flex flex-wrap gap-1.5 mt-3">{resource.subjects.slice(0,5).map(subject => <span key={subject} className="text-[10px] rounded-full bg-[#F5F0E8] px-2 py-1 text-[#2F4731]/70">{subject}</span>)}</div>
                <div className="mt-4 rounded-xl bg-[#FFFEF7] border border-[#E7DAC3] p-3">
                  <div className="flex items-center gap-2 mb-1"><ShieldCheck className="w-4 h-4 text-[#BD6809]" /><span className="text-xs font-black text-[#2F4731]">{policy.short}</span></div>
                  <p className="text-[11px] leading-relaxed text-[#2F4731]/55">{resource.licenseNote}</p>
                </div>
                <div className="mt-4">
                  <p className="text-[10px] font-black uppercase tracking-wider text-[#2F4731]/45 mb-1">Mission seed</p>
                  <p className="text-xs text-[#2F4731]/70">{resource.missionIdeas[0]}</p>
                </div>
                <a href={resource.url} target="_blank" rel="noreferrer" className="mt-auto pt-5 inline-flex items-center gap-2 text-sm font-bold text-[#BD6809] hover:text-[#2F4731]">
                  Open source <ExternalLink className="w-4 h-4" />
                </a>
              </article>
            );
          })}
        </div>
      </div>
    </div>
  );
}
