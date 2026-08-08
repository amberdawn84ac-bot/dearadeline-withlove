'use client';

import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import { BookOpen, Compass, FileText, GraduationCap, Hammer, Home, Map, MessageCircle, Send, Sparkles } from 'lucide-react';
import { listActivities, reportActivity, streamConversation } from '@/lib/brain-client';
import type { ActivityEntry, ActivityReportResponse, ConversationMessage } from '@/lib/brain-client';
import SketchnoteCard, { type SketchnoteData } from '@/components/SketchnoteCard';
import { saveSketchnote } from '@/lib/journal-client';

type Props = { studentId: string; studentName: string; gradeLevel: string };
type ChatMessage = { id: string; role: 'user' | 'adeline'; text: string; credit?: ActivityReportResponse; sketchNote?: SketchnoteData };

const ACTIVITY_RE = /\b(i (spent|did|worked|practiced|baked|built|planted|made|helped|cooked|studied|read|drew|painted|sewed|fixed|repaired|cleaned|volunteered)|today i|this (morning|afternoon|evening|week)|i've been|we (built|fixed|made|worked|planted|cooked|repaired))\b/i;

function id() { return `${Date.now()}-${Math.random().toString(36).slice(2)}`; }
function parseMinutes(text: string): number | null {
  const hours = text.match(/(\d+(?:\.\d+)?)\s*hour/i);
  const minutes = text.match(/(\d+)\s*min/i);
  if (/\ban hour\b/i.test(text) && !hours) return 60;
  if (/half.{0,5}hour/i.test(text) && !minutes) return 30;
  let total = 0;
  if (hours) total += Number(hours[1]) * 60;
  if (minutes) total += Number(minutes[1]);
  return total > 0 ? Math.round(total) : null;
}

function normalizeSketchnote(block: Record<string, unknown>): SketchnoteData {
  const rawSections = Array.isArray(block.sections) ? block.sections : [];
  return {
    title: typeof block.title === 'string' ? block.title : 'Something worth keeping',
    big_idea: typeof block.big_idea === 'string' ? block.big_idea : undefined,
    sections: rawSections.slice(0, 6).map((item) => {
      const section = item && typeof item === 'object' ? item as Record<string, unknown> : {};
      return {
        heading: typeof section.heading === 'string' ? section.heading : 'Note',
        text: typeof section.text === 'string' ? section.text : '',
        symbol: typeof section.symbol === 'string' ? section.symbol : undefined,
      };
    }).filter((section) => section.text),
    keywords: Array.isArray(block.keywords) ? block.keywords.filter((word): word is string => typeof word === 'string').slice(0, 8) : [],
    footer: typeof block.footer === 'string' ? block.footer : undefined,
    track: typeof block.track === 'string' ? block.track : undefined,
  };
}

export default function ConciergeDashboard({ studentId, studentName, gradeLevel }: Props) {
  const firstName = studentName?.trim().split(/\s+/)[0] || 'there';
  const [messages, setMessages] = useState<ChatMessage[]>([{ id: 'welcome', role: 'adeline', text: `Hey ${firstName}. What have you been up to? You can tell me anything.` }]);
  const [history, setHistory] = useState<ConversationMessage[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [pendingActivity, setPendingActivity] = useState<string | null>(null);
  const [activities, setActivities] = useState<ActivityEntry[]>([]);
  const [activityCredits, setActivityCredits] = useState(0);
  const bottomRef = useRef<HTMLDivElement>(null);
  const gameUrl = process.env.NEXT_PUBLIC_ADELINE_GAME_URL;

  useEffect(() => {
    listActivities(studentId).then((r) => { setActivities(r.activities.slice(0, 4)); setActivityCredits(r.total_credits); }).catch(() => undefined);
  }, [studentId]);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, busy]);

  async function fileActivity(description: string, minutes: number) {
    const result = await reportActivity({ student_id: studentId, grade_level: gradeLevel, description, time_minutes: minutes });
    setMessages((prev) => [...prev, { id: id(), role: 'adeline', text: result.adeline_note, credit: result }]);
    setActivities((prev) => [{
      activity_id: result.activity_id,
      course_title: result.course_title,
      activity_description: result.activity_description,
      credit_hours: result.credit_hours,
      primary_track: result.credited_tracks[0]?.track ?? 'ENGLISH_LITERATURE',
      credit_type: result.credited_tracks[0]?.credit_type ?? 'ELECTIVE',
      activity_date: new Date().toISOString().slice(0, 10),
      sealed_at: new Date().toISOString(),
    }, ...prev].slice(0, 4));
    setActivityCredits((prev) => Number((prev + result.credit_hours).toFixed(3)));
  }

  async function send() {
    const text = input.trim();
    if (!text || busy) return;
    setInput('');
    setMessages((prev) => [...prev, { id: id(), role: 'user', text }]);
    setBusy(true);
    try {
      if (pendingActivity) {
        const minutes = parseMinutes(text);
        if (!minutes) {
          setMessages((prev) => [...prev, { id: id(), role: 'adeline', text: 'About how long did it take? A rough guess is fine.' }]);
          return;
        }
        const activity = pendingActivity;
        setPendingActivity(null);
        await fileActivity(activity, minutes);
        return;
      }

      if (ACTIVITY_RE.test(text)) {
        const minutes = parseMinutes(text);
        if (!minutes) {
          setPendingActivity(text);
          setMessages((prev) => [...prev, { id: id(), role: 'adeline', text: 'That counts for more than you might think. About how long were you working on it?' }]);
          return;
        }
        await fileActivity(text, minutes);
        return;
      }

      const streamingId = id();
      setMessages((prev) => [...prev, { id: streamingId, role: 'adeline', text: '' }]);
      let responseText = '';
      for await (const event of streamConversation({ studentId, message: text, gradeLevel, history })) {
        if (event.type === 'text') {
          responseText += event.delta;
          setMessages((prev) => prev.map((m) => m.id === streamingId ? { ...m, text: responseText } : m));
        } else if (event.type === 'block') {
          if (event.block_type === 'SKETCHNOTE_NOTE') {
            const note = normalizeSketchnote(event as Record<string, unknown>);
            setMessages((prev) => prev.map((m) => m.id === streamingId ? { ...m, sketchNote: note } : m));
          } else {
            const addition = [typeof event.title === 'string' ? event.title : '', typeof event.content === 'string' ? event.content : ''].filter(Boolean).join('\n');
            responseText += `${responseText ? '\n\n' : ''}${addition}`;
            setMessages((prev) => prev.map((m) => m.id === streamingId ? { ...m, text: responseText } : m));
          }
        } else if (event.type === 'error') {
          responseText = 'I lost the thread for a second. Tell me that again?';
          setMessages((prev) => prev.map((m) => m.id === streamingId ? { ...m, text: responseText } : m));
        }
      }
      setHistory((prev) => [...prev, { role: 'user', content: text }, { role: 'adeline', content: responseText }].slice(-12));
    } catch {
      setMessages((prev) => [...prev, { id: id(), role: 'adeline', text: 'Something tripped over itself. Try that once more.' }]);
    } finally {
      setBusy(false);
    }
  }

  const placeholder = pendingActivity ? 'About how long did it take?' : 'Tell Adeline what happened, what you made, what you are wondering about...';

  return (
    <div className="min-h-screen bg-[#f5f0e5] text-[#243a2a] lg:h-screen lg:overflow-hidden">
      <div className="grid min-h-screen lg:h-screen lg:grid-cols-[250px_minmax(0,1fr)_300px]">
        <aside className="hidden bg-[#244a35] px-5 py-6 text-[#fbf5e7] lg:flex lg:flex-col">
          <div className="mb-8 flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-full border border-white/20 bg-[#ead8a8] font-serif text-xl text-[#244a35]">A</div>
            <div><p className="font-serif text-xl leading-none">Dear Adeline</p><p className="mt-1 text-[10px] uppercase tracking-[.2em] text-white/50">with love</p></div>
          </div>
          <nav className="space-y-1 text-sm">
            <Nav href="/dashboard" icon={<Home size={17} />} label="Home" active />
            <Nav href="/dashboard/journal" icon={<BookOpen size={17} />} label="Daily Journal" />
            <Nav href="/dashboard/portfolio" icon={<FileText size={17} />} label="Portfolio" />
            <Nav href="/dashboard/projects" icon={<Hammer size={17} />} label="Project Library" />
            <Nav href="/dashboard/opportunities" icon={<Compass size={17} />} label="Local Intelligence" />
            <Nav href="/dashboard/graduation" icon={<GraduationCap size={17} />} label="Graduation" />
          </nav>
          <div className="mt-auto border-t border-white/10 pt-5">
            <p className="text-[10px] uppercase tracking-[.18em] text-white/45">The other door</p>
            {gameUrl ? <a href={gameUrl} className="mt-3 flex items-center gap-3 rounded-xl bg-[#c18a2b] px-3 py-3 text-sm font-semibold text-white"><Map size={18} /> Enter the game world</a> : <div className="mt-3 flex items-center gap-3 rounded-xl border border-white/15 px-3 py-3 text-sm text-white/55"><Map size={18} /> Game world connection</div>}
          </div>
        </aside>

        <main className="flex min-h-[100dvh] flex-col bg-[#fbf7ec] lg:min-h-0">
          <header className="border-b border-[#d9cfbb] px-5 py-4 sm:px-8">
            <div className="mx-auto flex max-w-4xl items-center justify-between gap-4">
              <div><p className="text-[10px] uppercase tracking-[.22em] text-[#8b7b66]">Adeline</p><h1 className="font-serif text-2xl text-[#213f2d]">I&apos;m here.</h1></div>
              <div className="rounded-full border border-[#d8ccb7] bg-white/60 px-3 py-1.5 text-xs text-[#746654]">{activityCredits ? `${activityCredits.toFixed(2)} activity credits filed` : 'Nothing filed yet'}</div>
            </div>
          </header>

          <section className="flex-1 overflow-y-auto px-4 py-6 sm:px-8">
            <div className="mx-auto max-w-4xl space-y-6">
              {messages.map((message) => <div key={message.id} className={message.role === 'user' ? 'flex justify-end' : 'flex justify-start'}>
                <div className={message.role === 'user' ? 'max-w-[82%] rounded-[22px_22px_5px_22px] bg-[#244a35] px-4 py-3 text-sm leading-relaxed text-[#fffaf0]' : 'max-w-[92%] rounded-[5px_22px_22px_22px] border border-[#ded2bc] bg-[#fffdf7] px-4 py-3 text-sm leading-relaxed text-[#354b3b] shadow-[0_5px_18px_rgba(74,57,35,.05)]'}>
                  {message.text && <p className="whitespace-pre-wrap">{message.text}</p>}
                  {!message.text && busy && <p>…</p>}
                  {message.sketchNote && <SketchnoteCard note={message.sketchNote} onSave={() => saveSketchnote(studentId, message.sketchNote!)} />}
                  {message.credit && <CreditReceipt result={message.credit} />}
                </div>
              </div>)}
              <div ref={bottomRef} />
            </div>
          </section>

          <div className="border-t border-[#d9cfbb] bg-[#f7f1e4] px-4 py-4 sm:px-8">
            <div className="mx-auto max-w-4xl">
              <div className="flex items-end gap-3 rounded-[24px_18px_24px_18px] border border-[#cfc2ab] bg-[#fffdf7] p-3 shadow-[0_8px_24px_rgba(67,51,31,.07)]">
                <MessageCircle className="mb-2 hidden text-[#9c7a39] sm:block" size={18} />
                <textarea value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void send(); } }} rows={2} placeholder={placeholder} className="min-h-[52px] flex-1 resize-none bg-transparent px-1 py-2 text-sm outline-none placeholder:text-[#9a8b76]" />
                <button onClick={() => void send()} disabled={!input.trim() || busy} aria-label="Send" className="mb-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#9a4d71] text-white transition hover:scale-[1.03] disabled:opacity-35"><Send size={16} /></button>
              </div>
              <div className="mt-2 flex flex-wrap items-center justify-center gap-x-4 gap-y-1 text-[10px] text-[#8c7c67]"><span>Tell her about real life.</span><span>Ask for a story, project, lesson, note, or adventure when you want one.</span></div>
            </div>
          </div>
        </main>

        <aside className="hidden overflow-y-auto border-l border-[#d7cbb7] bg-[#f1eadc] p-5 lg:block">
          <SideCard title="What Adeline noticed" jewel="#355b84"><p className="text-sm leading-relaxed text-[#526154]">Real work can become transcript evidence. Questions can become illustrated notes. Curiosity can become a lesson, project, investigation, or adventure.</p></SideCard>
          <SideCard title="Recently counted" jewel="#8e3f69">{activities.length === 0 ? <p className="text-sm text-[#7e725f]">Tell Adeline what you&apos;ve been doing and this will begin filling itself in.</p> : <div className="space-y-3">{activities.map((activity) => <div key={activity.activity_id} className="border-b border-[#cfc2ac]/60 pb-3 last:border-0 last:pb-0"><p className="font-serif text-sm text-[#2c4c36]">{activity.course_title}</p><p className="mt-1 text-[11px] text-[#7c6d59]">{activity.credit_hours} credit hrs · {activity.credit_type.toLowerCase()}</p></div>)}</div>}</SideCard>
          <SideCard title="Doors she can open" jewel="#aa7a24"><div className="space-y-2 text-sm text-[#4c5c4f]"><p>“Sketch that out for me.”</p><p>“Turn this into a project.”</p><p>“Teach me why that happened.”</p><p>“Give me somewhere to investigate.”</p></div></SideCard>
          <div className="mt-5 rounded-[24px_17px_24px_18px] bg-[#274d39] p-5 text-[#fbf5e8] shadow-lg"><Sparkles size={18} className="text-[#d7a63f]" /><p className="mt-3 font-serif text-lg">Nothing has to become school.</p><p className="mt-2 text-xs leading-relaxed text-white/65">Sometimes Adeline just talks. When something is worth keeping, she can turn it into a page for the daily journal.</p></div>
        </aside>
      </div>
    </div>
  );
}

function Nav({ href, icon, label, active = false }: { href: string; icon: React.ReactNode; label: string; active?: boolean }) {
  return <Link href={href} className={`flex items-center gap-3 rounded-xl px-3 py-2.5 transition ${active ? 'bg-white/10 text-white' : 'text-white/65 hover:bg-white/5 hover:text-white'}`}>{icon}<span>{label}</span></Link>;
}

function SideCard({ title, jewel, children }: { title: string; jewel: string; children: React.ReactNode }) {
  return <section className="mb-4 rounded-[22px_16px_24px_18px] border border-[#d4c6ae] bg-[#fffaf0] p-4 shadow-[0_4px_14px_rgba(72,54,33,.05)]"><div className="mb-3 flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full" style={{ background: jewel, boxShadow: `0 0 12px ${jewel}55` }} /><h2 className="font-serif text-base text-[#284632]">{title}</h2></div>{children}</section>;
}

function CreditReceipt({ result }: { result: ActivityReportResponse }) {
  return <div className="mt-3 border-t border-[#d8ccb8] pt-3"><p className="text-[10px] font-bold uppercase tracking-[.15em] text-[#8d5d1d]">Filed toward graduation</p><p className="mt-1 font-serif text-base text-[#284632]">{result.course_title}</p><p className="mt-1 text-xs text-[#6e6659]">{result.credit_hours} credit hours · {result.credited_tracks.slice(0, 2).map((t) => t.track.replaceAll('_', ' ').toLowerCase()).join(' + ')}</p></div>;
}
