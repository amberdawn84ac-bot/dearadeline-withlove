'use client';

import { FormEvent, useEffect, useMemo, useState } from 'react';
import styles from '@/components/nav/sites-dashboard.module.css';

type Scope = 'LOCAL' | 'STATE' | 'NATIONAL';
type Opportunity = {
  id: string; title: string; url: string; source: string; scope: Scope;
  category: string; location: string; grades: string; description: string;
  deadline?: string | null; verification_status: 'LIVE_SOURCE' | 'DIRECTORY';
  parent_review_required: boolean;
};

const CATEGORIES = [
  ['', 'Everything'], ['ACADEMIC', 'Spelling & Academic'], ['SCIENCE_MATH', 'Science & Math'],
  ['ART_DESIGN', 'Art & Design'], ['WRITING_POETRY', 'Writing & Poetry'],
  ['SCHOLARSHIP', 'Scholarships'], ['PAID_WORK', 'Paid & Commissioned Work'],
] as const;

export default function OpportunitiesPage() {
  const [location, setLocation] = useState('');
  const [searchLocation, setSearchLocation] = useState('');
  const [category, setCategory] = useState('');
  const [items, setItems] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [safetyNote, setSafetyNote] = useState('');

  async function load(nextLocation = searchLocation) {
    setLoading(true); setError('');
    try {
      const params = new URLSearchParams();
      if (nextLocation.trim()) params.set('location', nextLocation.trim());
      const response = await fetch(`/brain/api/opportunities${params.size ? `?${params}` : ''}`, { credentials: 'include', cache: 'no-store' });
      if (!response.ok) throw new Error(response.status === 401 ? 'Please sign in again.' : 'Opportunities could not be loaded.');
      const data = await response.json();
      setItems(data.opportunities ?? []);
      setSafetyNote(data.safety_note ?? '');
      if (!location && data.profile?.location) setLocation(data.profile.location);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Opportunities could not be loaded.');
    } finally { setLoading(false); }
  }

  useEffect(() => { void load(''); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const filtered = useMemo(() => category ? items.filter((item) => item.category === category) : items, [items, category]);

  function submit(event: FormEvent) {
    event.preventDefault();
    setSearchLocation(location.trim());
    void load(location.trim());
  }

  return (
    <div className={styles.todayWorkspace}>
      <header className={styles.todayTitle}>
        <h1>Opportunities</h1>
        <span>Contests, scholarships, challenges, and real-world openings that homeschool families may not otherwise hear about.</span>
      </header>

      <form onSubmit={submit} className="mb-5 flex flex-wrap gap-2 rounded-2xl border border-[#d8ccb8] bg-white p-4">
        <label className="min-w-[220px] flex-1 text-sm font-bold text-[#294c35]">City, county, or ZIP
          <input value={location} onChange={(event) => setLocation(event.target.value)} placeholder="Nowata County, Oklahoma" className="mt-1 w-full rounded-xl border border-[#d8ccb8] px-3 py-2 font-normal" />
        </label>
        <button className="self-end rounded-xl bg-[#294c35] px-5 py-2.5 font-bold text-white" type="submit">Find nearby opportunities</button>
      </form>

      <div className="mb-5 flex flex-wrap gap-2" aria-label="Opportunity categories">
        {CATEGORIES.map(([value, label]) => <button key={label} type="button" onClick={() => setCategory(value)} className={`rounded-full border px-3 py-2 text-xs font-bold ${category === value ? 'border-[#294c35] bg-[#294c35] text-white' : 'border-[#d8ccb8] bg-white text-[#294c35]'}`}>{label}</button>)}
      </div>

      {safetyNote && <p className="mb-5 rounded-xl bg-[#fff4df] p-3 text-sm text-[#71440d]">Parent check: {safetyNote}</p>}
      {loading && <p className={styles.loading}>Adeline is checking official opportunity sources…</p>}
      {error && <p className={styles.error} role="alert">{error}</p>}

      {!loading && !error && (['LOCAL', 'STATE', 'NATIONAL'] as Scope[]).map((scope) => {
        const group = filtered.filter((item) => item.scope === scope);
        if (!group.length) return null;
        return <section key={scope} className="mb-7">
          <h2 className="mb-3 font-serif text-2xl text-[#294c35]">{scope === 'LOCAL' ? 'Near you' : scope === 'STATE' ? 'Across your state' : 'National'}</h2>
          <div className="grid gap-3 lg:grid-cols-2">
            {group.map((item) => <article key={item.id} className="rounded-2xl border border-[#d8ccb8] bg-white p-4 shadow-sm">
              <div className="mb-2 flex flex-wrap gap-2 text-[10px] font-bold uppercase tracking-wide text-[#8a5a25]"><span>{item.category.replace(/_/g, ' ')}</span><span>·</span><span>{item.verification_status === 'LIVE_SOURCE' ? 'Current source' : 'Official directory'}</span></div>
              <h3 className="text-lg font-bold text-[#294c35]">{item.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-[#294c35]/80">{item.description}</p>
              <p className="mt-3 text-xs text-[#294c35]/65">{item.grades}{item.deadline ? ` · Deadline: ${item.deadline}` : ' · Check the current deadline'}</p>
              {item.parent_review_required && <p className="mt-2 text-xs font-bold text-[#9a3e20]">Parent review required before applying</p>}
              <a href={item.url} target="_blank" rel="noopener noreferrer" className="mt-3 inline-flex rounded-lg bg-[#bd6809] px-3 py-2 text-xs font-bold text-white">Open {item.source} ↗</a>
            </article>)}
          </div>
        </section>;
      })}
      {!loading && !error && !filtered.length && <p className="rounded-2xl border border-[#d8ccb8] bg-white p-5 text-[#294c35]">No matches in this category right now. Try Everything or update the location.</p>}
    </div>
  );
}
