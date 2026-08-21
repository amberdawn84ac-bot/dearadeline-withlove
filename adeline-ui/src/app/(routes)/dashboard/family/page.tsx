'use client';

import { FormEvent, useCallback, useEffect, useState } from 'react';
import { Gamepad2, Loader2, MessageCircle, Users, Wrench } from 'lucide-react';

type Kind = 'MESSAGE' | 'PROJECT' | 'GAME';
interface Member { id: string; name: string; role: string; gradeLevel?: string | null }
interface Post { id: string; authorName: string; kind: Kind; title?: string | null; body: string; resourceUrl?: string | null; createdAt: string }
interface Feed { members: Member[]; posts: Post[] }

const KIND_META = {
  MESSAGE: { label: 'Message', icon: MessageCircle },
  PROJECT: { label: 'Project invitation', icon: Wrench },
  GAME: { label: 'Game invitation', icon: Gamepad2 },
} as const;

export default function FamilyRoomPage() {
  const [feed, setFeed] = useState<Feed | null>(null);
  const [kind, setKind] = useState<Kind>('MESSAGE');
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [resourceUrl, setResourceUrl] = useState('');
  const [status, setStatus] = useState<'loading' | 'ready' | 'saving' | 'error'>('loading');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      const response = await fetch('/brain/family/feed', { credentials: 'include', cache: 'no-store' });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || 'The family room could not be opened.');
      setFeed(data);
      setStatus('ready');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The family room could not be opened.');
      setStatus('error');
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setStatus('saving');
    setError('');
    try {
      const response = await fetch('/brain/family/feed', {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ kind, title: title.trim() || null, body, resource_url: resourceUrl.trim() || null }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.detail || 'That note could not be shared.');
      setTitle(''); setBody(''); setResourceUrl('');
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'That note could not be shared.');
      setStatus('error');
    }
  }

  if (status === 'loading') return <div className="grid min-h-[50vh] place-items-center text-[#2F4731]"><Loader2 className="animate-spin" /></div>;

  return (
    <div className="mx-auto max-w-5xl p-5 md:p-8 text-[#2F4731]">
      <header className="mb-6">
        <p className="text-xs font-black uppercase tracking-[.18em] text-[#BD6809]">One household · individual learning records</p>
        <h1 className="mt-2 text-4xl" style={{ fontFamily: 'var(--font-emilys-candy), cursive' }}>Family Room</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-[#2F4731]/70">Talk together, share a game, or invite the family into a project. Adeline records mastery and credit separately for what each learner demonstrates.</p>
      </header>

      {error && <p className="mb-4 rounded-xl bg-[#fae2dc] p-3 text-sm font-bold text-[#8a352b]">{error}</p>}

      {feed && <section className="mb-6 rounded-2xl border border-[#E7DAC3] bg-white p-5">
        <div className="mb-3 flex items-center gap-2 font-bold"><Users size={19} /> Your household</div>
        <div className="flex flex-wrap gap-2">{feed.members.map(member => <span key={member.id} className="rounded-full bg-[#edf4ea] px-3 py-1.5 text-xs font-bold">{member.name}{member.role === 'STUDENT' && member.gradeLevel ? ` · Grade ${member.gradeLevel === 'K' ? 'K' : member.gradeLevel}` : ''}</span>)}</div>
      </section>}

      <div className="grid gap-6 lg:grid-cols-[.9fr_1.1fr]">
        <form onSubmit={submit} className="h-fit rounded-2xl border border-[#E7DAC3] bg-white p-5 space-y-4">
          <h2 className="text-lg font-bold">Share with the family</h2>
          <div className="grid grid-cols-3 gap-2">{(Object.keys(KIND_META) as Kind[]).map(value => {
            const Icon = KIND_META[value].icon;
            return <button key={value} type="button" onClick={() => setKind(value)} className={`rounded-xl border p-2 text-xs font-bold ${kind === value ? 'border-[#2F4731] bg-[#edf4ea]' : 'border-[#E7DAC3]'}`}><Icon className="mx-auto mb-1" size={17} />{KIND_META[value].label}</button>;
          })}</div>
          {kind !== 'MESSAGE' && <input value={title} onChange={event => setTitle(event.target.value)} maxLength={120} placeholder={kind === 'GAME' ? 'What should we play?' : 'What should we build?'} className="w-full rounded-xl border border-[#d7cdbb] px-3 py-3 text-sm" />}
          <textarea required minLength={1} maxLength={2000} rows={5} value={body} onChange={event => setBody(event.target.value)} placeholder="Write a note, suggest roles, or tell everyone when you are ready…" className="w-full rounded-xl border border-[#d7cdbb] px-3 py-3 text-sm" />
          {kind !== 'MESSAGE' && <input type="url" value={resourceUrl} onChange={event => setResourceUrl(event.target.value)} placeholder="Optional project or game link" className="w-full rounded-xl border border-[#d7cdbb] px-3 py-3 text-sm" />}
          <button disabled={status === 'saving'} className="w-full rounded-xl bg-[#2F4731] px-4 py-3 font-bold text-white disabled:opacity-50">{status === 'saving' ? 'Sharing…' : 'Share with family'}</button>
        </form>

        <section className="space-y-3">
          <h2 className="text-lg font-bold">Family board</h2>
          {feed?.posts.length === 0 && <div className="rounded-2xl border border-dashed border-[#cdbfa8] p-8 text-center text-sm text-[#2F4731]/60">No notes yet. Invite someone into the first game or project.</div>}
          {feed?.posts.map(post => {
            const Icon = KIND_META[post.kind].icon;
            return <article key={post.id} className="rounded-2xl border border-[#E7DAC3] bg-white p-5">
              <div className="flex items-center justify-between gap-3"><span className="flex items-center gap-2 text-xs font-black uppercase tracking-wide text-[#BD6809]"><Icon size={16} />{KIND_META[post.kind].label}</span><time className="text-[11px] text-[#2F4731]/45">{new Date(post.createdAt).toLocaleString()}</time></div>
              {post.title && <h3 className="mt-3 font-bold">{post.title}</h3>}
              <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-[#2F4731]/75">{post.body}</p>
              <div className="mt-3 flex items-center justify-between gap-3"><span className="text-xs font-bold">— {post.authorName}</span>{post.resourceUrl && <a href={post.resourceUrl} target="_blank" rel="noopener noreferrer" className="rounded-lg bg-[#edf4ea] px-3 py-2 text-xs font-bold text-[#2F4731] no-underline">Open together</a>}</div>
            </article>;
          })}
        </section>
      </div>
    </div>
  );
}
