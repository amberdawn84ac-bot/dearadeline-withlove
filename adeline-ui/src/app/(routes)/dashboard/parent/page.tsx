'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import {
  ArrowLeft, ArrowRight, BookHeart, CheckCircle2, ChevronRight, CircleDashed,
  Compass, ExternalLink, GraduationCap, Lightbulb, Link2, Loader2, Plus,
  Search, Settings, Users,
} from 'lucide-react';
import {
  addStudent, getFamilyDashboard, type FamilyDashboard, type StudentProgress,
} from '@/lib/parent-client';
import { getLessonPortfolio, type LessonPortfolioItem } from '@/lib/brain-client';
import { AddStudentDialog } from '@/components/parent/AddStudentDialog';
import { ClaimStudentDialog } from '@/components/parent/ClaimStudentDialog';
import { ParentAdelinePanel } from '@/components/parent/ParentAdelinePanel';

const TRACK_LABELS: Record<string, string> = {
  CREATION_SCIENCE: 'Creation Science', HEALTH_NATUROPATHY: 'Health & Naturopathy',
  HOMESTEADING: 'Homesteading', GOVERNMENT_ECONOMICS: 'Government & Economics',
  JUSTICE_CHANGEMAKING: 'Justice & Changemaking', DISCIPLESHIP: 'Discipleship',
  TRUTH_HISTORY: 'Truth & History', ENGLISH_LITERATURE: 'English & Literature',
  APPLIED_MATHEMATICS: 'Applied Mathematics', CREATIVE_ECONOMY: 'Creative Economy',
};

const PROFICIENCY_LABELS = {
  NOT_STARTED: 'Not yet explored',
  DEVELOPING: 'Introduced · more experience will help',
  APPROACHING: 'Taking shape · more evidence is needed',
  UNDERSTANDING: 'Demonstrated with evidence',
  EXTENDING: 'Demonstrated and applied deeply',
};

function gradeLabel(grade: string) {
  return grade === 'K' ? 'Kindergarten' : grade === 'PLACEMENT' ? 'Placement in progress' : `Grade ${grade}`;
}

function trackLabel(track?: string | null) {
  return track ? TRACK_LABELS[track] ?? track.replace(/_/g, ' ') : 'Learning across subjects';
}

function ChildCard({ student, onSelect }: { student: StudentProgress; onSelect: () => void }) {
  const current = student.learning?.current_learning[0];
  return (
    <button onClick={onSelect} className="group flex min-h-72 flex-col rounded-[24px] border border-[#D8C9B2] bg-[#FFFDF7] p-5 text-left transition hover:-translate-y-1 hover:border-[#BD6809] hover:shadow-[0_15px_35px_rgba(62,50,33,.10)]">
      <div className="flex items-start justify-between gap-3">
        <div className="grid h-11 w-11 place-items-center rounded-full bg-[#E7EFE5] text-lg font-black text-[#2F6542]">{student.student_name.slice(0, 1).toUpperCase()}</div>
        <ChevronRight className="h-5 w-5 text-[#2F4731]/30 transition group-hover:translate-x-1 group-hover:text-[#BD6809]" />
      </div>
      <h3 className="mt-4 text-2xl font-bold" style={{ fontFamily: 'var(--font-emilys-candy), cursive' }}>{student.student_name}</h3>
      <p className="mt-1 text-xs font-bold uppercase tracking-[.12em] text-[#2F4731]/45">{gradeLabel(student.grade_level)}</p>
      <div className="mt-5 flex-1">
        <p className="text-[10px] font-black uppercase tracking-[.14em] text-[#9A3F4A]">Current learning</p>
        <p className="mt-2 text-sm font-bold leading-5">{current?.title || trackLabel(student.active_track)}</p>
        <p className="mt-2 line-clamp-3 text-xs leading-5 text-[#2F4731]/60">{current?.description || 'Adeline is gathering enough evidence to shape the next meaningful direction.'}</p>
      </div>
      <div className="mt-5 flex flex-wrap gap-2 border-t border-[#E1D5C3] pt-4 text-[11px] font-bold text-[#2F4731]/62">
        <span>{student.learning?.coverage.mastered ?? 0} concepts demonstrated</span><span aria-hidden="true">•</span><span>{student.projects_sealed} project {student.projects_sealed === 1 ? 'entry' : 'entries'}</span>
      </div>
    </button>
  );
}

function ChildOverview({ student, portfolio, portfolioLoading, onClose }: {
  student: StudentProgress;
  portfolio: LessonPortfolioItem[];
  portfolioLoading: boolean;
  onClose: () => void;
}) {
  const learning = student.learning;
  const graduation = learning?.graduation_progress;
  return (
    <section className="rounded-[30px] border border-[#CFC1A8] bg-[#FFFDF7] p-5 shadow-[0_20px_50px_rgba(62,50,33,.08)] sm:p-8">
      <button onClick={onClose} className="inline-flex items-center gap-2 text-xs font-black uppercase tracking-[.14em] text-[#9A3F4A]"><ArrowLeft className="h-4 w-4" /> Back to the whole family</button>
      <div className="mt-5 flex flex-col gap-3 border-b border-[#DED1BD] pb-6 sm:flex-row sm:items-end sm:justify-between">
        <div><p className="text-xs font-black uppercase tracking-[.16em] text-[#BD6809]">Parent learning overview</p><h2 className="mt-1 text-4xl font-bold" style={{ fontFamily: 'var(--font-emilys-candy), cursive' }}>{student.student_name}</h2><p className="mt-2 text-sm text-[#2F4731]/62">What is being investigated, what has been demonstrated, and where learning may go next.</p></div>
        <span className="rounded-full bg-[#E7EFE5] px-4 py-2 text-xs font-black text-[#2F6542]">{gradeLabel(student.grade_level)}</span>
      </div>

      <div className="mt-7 grid gap-6 lg:grid-cols-2">
        <div className="space-y-6">
          <section className="rounded-2xl border border-[#DED1BD] p-5">
            <p className="flex items-center gap-2 text-xs font-black uppercase tracking-[.14em] text-[#9A3F4A]"><Search className="h-4 w-4" /> Current learning</p>
            <div className="mt-4 space-y-4">
              {(learning?.current_learning ?? []).map((item) => <div key={item.id} className="border-b border-[#E7DAC3] pb-4 last:border-0 last:pb-0"><p className="font-bold">{item.title}</p><p className="mt-1 text-xs font-bold text-[#BD6809]">{trackLabel(item.track)}</p><p className="mt-2 text-sm leading-6 text-[#2F4731]/65">{item.description}</p></div>)}
              {!learning?.current_learning.length && <p className="text-sm text-[#2F4731]/60">The next investigation is still being shaped from conversation and evidence.</p>}
            </div>
          </section>

          <section className="rounded-2xl border border-[#DED1BD] p-5">
            <p className="flex items-center gap-2 text-xs font-black uppercase tracking-[.14em] text-[#2F6542]"><CheckCircle2 className="h-4 w-4" /> Mastery & progress</p>
            <div className="mt-4 flex items-end gap-2"><span className="text-4xl font-black">{learning?.coverage.mastered ?? 0}</span><span className="pb-1 text-sm text-[#2F4731]/55">concepts demonstrated with evidence</span></div>
            <div className="mt-5 grid gap-2 sm:grid-cols-2">{(learning?.coverage.subjects ?? []).map((subject) => <div key={subject.subject} className="rounded-xl bg-[#F3E8D5] p-3"><p className="text-xs font-bold">{subject.subject}</p><p className="mt-1 text-xs text-[#2F4731]/58">{subject.mastered} demonstrated · {subject.remaining} still available to explore</p></div>)}</div>
          </section>

          <section className="rounded-2xl border border-[#DED1BD] p-5">
            <p className="flex items-center gap-2 text-xs font-black uppercase tracking-[.14em] text-[#BD6809]"><Lightbulb className="h-4 w-4" /> Areas to explore</p>
            <p className="mt-3 text-sm leading-6 text-[#2F4731]/62">Useful possibilities for more experience or evidence—not a judgment that {student.student_name} is “behind.”</p>
            <div className="mt-4 space-y-3">{(learning?.areas_to_explore ?? []).map((area) => <div key={area.standard_id} className="flex gap-3"><CircleDashed className="mt-0.5 h-4 w-4 shrink-0 text-[#BD6809]" /><div><p className="text-sm font-semibold leading-5">{area.description}</p><p className="mt-1 text-[10px] font-black uppercase tracking-[.12em] text-[#2F4731]/42">{PROFICIENCY_LABELS[area.proficiency]}</p></div></div>)}{learning && learning.areas_to_explore.length === 0 && <p className="text-sm text-[#2F4731]/60">No additional concepts are flagged in the current persisted plan.</p>}</div>
          </section>
        </div>

        <div className="space-y-6">
          <section className="rounded-2xl border border-[#DED1BD] p-5">
            <p className="flex items-center gap-2 text-xs font-black uppercase tracking-[.14em] text-[#5B314E]"><BookHeart className="h-4 w-4" /> Portfolio evidence</p>
            {portfolioLoading ? <div className="mt-5 flex items-center gap-2 text-sm text-[#2F4731]/55"><Loader2 className="h-4 w-4 animate-spin" /> Loading this learner&rsquo;s authorized portfolio…</div> : <div className="mt-4 space-y-3">{portfolio.slice(0, 5).map((item) => <div key={item.lesson_id} className="rounded-xl bg-[#F7F0E5] p-4"><p className="font-bold">{item.title}</p><p className="mt-1 text-xs font-semibold text-[#9A3F4A]">{trackLabel(item.track)}</p>{item.reflection && <p className="mt-2 line-clamp-3 text-sm leading-5 text-[#2F4731]/62">“{item.reflection}”</p>}{item.artifact_description && <p className="mt-2 text-xs text-[#2F4731]/52">Evidence: {item.artifact_description}</p>}</div>)}{portfolio.length === 0 && <p className="text-sm leading-6 text-[#2F4731]/60">Portfolio evidence will appear as {student.student_name} creates, investigates, reflects, and demonstrates understanding.</p>}</div>}
          </section>

          <section className="rounded-2xl border border-[#DED1BD] p-5">
            <p className="flex items-center gap-2 text-xs font-black uppercase tracking-[.14em] text-[#2F6542]"><GraduationCap className="h-4 w-4" /> Graduation & transcript</p>
            {graduation?.is_high_school ? <><div className="mt-4 grid grid-cols-3 gap-2"><div className="rounded-xl bg-[#E7EFE5] p-3"><p className="text-2xl font-black">{(graduation.total_earned ?? 0).toFixed(1)}</p><p className="text-[10px] font-bold uppercase text-[#2F4731]/45">Mastery credits</p></div><div className="rounded-xl bg-[#F3E8D5] p-3"><p className="text-2xl font-black">{(graduation.credits_remaining ?? 0).toFixed(1)}</p><p className="text-[10px] font-bold uppercase text-[#2F4731]/45">Still available</p></div><div className="rounded-xl bg-[#EEE4EC] p-3"><p className="text-2xl font-black">{portfolio.length}</p><p className="text-[10px] font-bold uppercase text-[#2F4731]/45">Evidence entries</p></div></div><div className="mt-4 space-y-2">{(learning?.credit_gaps ?? []).map((gap) => <div key={gap.bucket} className="flex justify-between gap-4 border-b border-[#E7DAC3] py-2 text-sm"><span className="font-semibold">{gap.bucket}</span><span className="text-[#2F4731]/55">{gap.earned.toFixed(1)} earned · {gap.remaining.toFixed(1)} remaining</span></div>)}</div></> : <p className="mt-4 text-sm leading-6 text-[#2F4731]/62">The record is building toward later transcript and graduation requirements through demonstrated concepts and portfolio evidence—not time spent.</p>}
          </section>

          <section className="rounded-2xl bg-[#5B314E] p-5 text-white"><p className="text-xs font-black uppercase tracking-[.14em] text-[#F0BE62]">Recent learning</p><p className="mt-3 text-sm leading-6 text-white/70">{student.last_activity ? `${student.student_name} last added sealed learning evidence on ${new Date(student.last_activity).toLocaleDateString()}.` : 'No sealed evidence is recorded yet.'}</p><p className="mt-3 text-xs text-white/50">Current area: {trackLabel(student.active_track)}</p></section>
        </div>
      </div>
    </section>
  );
}

export default function ParentDashboardPage() {
  const [dashboard, setDashboard] = useState<FamilyDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAddStudent, setShowAddStudent] = useState(false);
  const [showClaimStudent, setShowClaimStudent] = useState(false);
  const [selectedStudentId, setSelectedStudentId] = useState<string | null>(null);
  const [portfolio, setPortfolio] = useState<LessonPortfolioItem[]>([]);
  const [portfolioLoading, setPortfolioLoading] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true); setError(null);
    try { setDashboard(await getFamilyDashboard()); }
    catch (caught) { setError(caught instanceof Error ? caught.message : 'The family dashboard could not be loaded.'); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { void fetchData(); }, [fetchData]);

  useEffect(() => {
    if (!selectedStudentId) { setPortfolio([]); return; }
    setPortfolioLoading(true);
    getLessonPortfolio(selectedStudentId).then(setPortfolio).catch(() => setPortfolio([])).finally(() => setPortfolioLoading(false));
  }, [selectedStudentId]);

  const selectedStudent = dashboard?.students.find((item) => item.student_id === selectedStudentId) ?? null;

  async function handleAddStudent(name: string, username: string, pin: string, gradeLevel: string, privacyConsent: boolean) {
    await addStudent({ name, username, pin, grade_level: gradeLevel, privacy_consent: privacyConsent, privacy_notice_version: '2026-08-23' });
    setShowAddStudent(false); await fetchData();
  }

  if (loading) return <main className="grid min-h-screen place-items-center bg-[#F8F2E7] px-6"><div className="text-center"><Loader2 className="mx-auto h-8 w-8 animate-spin text-[#BD6809]" /><p className="mt-4 text-sm font-semibold text-[#2F4731]/65">Gathering the family&rsquo;s learning story…</p></div></main>;
  if (error) return <main className="grid min-h-screen place-items-center bg-[#F8F2E7] px-6"><div className="max-w-md rounded-3xl border border-[#E0CDB1] bg-white p-8 text-center"><h1 className="text-2xl font-bold text-[#2F4731]">The family view did not open</h1><p className="mt-3 text-sm text-[#9A3F4A]">{error}</p><button onClick={() => void fetchData()} className="mt-6 rounded-xl bg-[#2F4731] px-5 py-3 text-sm font-bold text-white">Try again</button></div></main>;

  const investigation = dashboard?.family_investigation;
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_10%_0%,rgba(189,104,9,.10),transparent_32%),radial-gradient(circle_at_100%_35%,rgba(92,49,78,.09),transparent_30%)] bg-[#F8F2E7] pb-16 text-[#2F4731]">
      <header className="border-b border-[#DCCFB9] bg-[#FFFDF7]/90"><div className="mx-auto flex max-w-7xl flex-col gap-5 px-5 py-7 sm:px-8 lg:flex-row lg:items-center lg:justify-between"><div><p className="text-xs font-black uppercase tracking-[.2em] text-[#9A3F4A]">Parent home</p><h1 className="mt-1 text-4xl font-bold sm:text-5xl" style={{ fontFamily: 'var(--font-emilys-candy), cursive' }}>Our Family</h1><p className="mt-2 max-w-2xl text-sm leading-6 text-[#2F4731]/65">See the whole story first—what your family is investigating, discovering, creating, and demonstrating.</p></div><nav className="flex flex-wrap gap-2" aria-label="Parent tools"><Link href="/dashboard/parent/resources" className="inline-flex items-center gap-2 rounded-full border border-[#CFC1A8] bg-white px-4 py-2.5 text-sm font-bold"><Compass className="h-4 w-4" /> Resource Vault</Link><Link href="/dashboard/family" className="inline-flex items-center gap-2 rounded-full border border-[#CFC1A8] bg-white px-4 py-2.5 text-sm font-bold"><Users className="h-4 w-4" /> Family room</Link><Link href="/dashboard/settings" className="grid h-10 w-10 place-items-center rounded-full border border-[#CFC1A8] bg-white" aria-label="Family settings"><Settings className="h-4 w-4" /></Link></nav></div></header>

      <div className="mx-auto max-w-7xl space-y-10 px-5 py-8 sm:px-8">
        {!dashboard?.students.length ? <section className="rounded-[30px] border border-[#D4C3A7] bg-[#FFFDF7] p-8 text-center sm:p-12"><Users className="mx-auto h-10 w-10 text-[#BD6809]" /><h2 className="mt-4 text-3xl font-bold" style={{ fontFamily: 'var(--font-emilys-candy), cursive' }}>Build your family connection</h2><p className="mx-auto mt-3 max-w-xl text-sm leading-6 text-[#2F4731]/65">Create a learner here or connect an existing learner. Existing learning stays with that learner; no account needs to be recreated.</p><div className="mt-6 flex flex-wrap justify-center gap-3"><button onClick={() => setShowClaimStudent(true)} className="inline-flex items-center gap-2 rounded-xl border border-[#2F4731]/20 bg-white px-5 py-3 text-sm font-bold"><Link2 className="h-4 w-4" /> Connect existing learner</button><button onClick={() => setShowAddStudent(true)} className="inline-flex items-center gap-2 rounded-xl bg-[#BD6809] px-5 py-3 text-sm font-bold text-white"><Plus className="h-4 w-4" /> Create learner</button></div></section> : <>
          <section className="overflow-hidden rounded-[30px] border border-[#C6B796] bg-[#FFFDF7] shadow-[0_18px_55px_rgba(62,50,33,.08)]"><div className="grid lg:grid-cols-[1.35fr_.65fr]"><div className="p-6 sm:p-9"><p className="flex items-center gap-2 text-xs font-black uppercase tracking-[.18em] text-[#9A3F4A]"><Search className="h-4 w-4" /> Family investigation</p>{investigation ? <><h2 className="mt-4 max-w-3xl text-3xl font-bold leading-tight sm:text-4xl" style={{ fontFamily: 'var(--font-emilys-candy), cursive' }}>{investigation.title}</h2><p className="mt-4 max-w-3xl text-base leading-7 text-[#2F4731]/72">{investigation.description}</p><div className="mt-6 grid gap-3 sm:grid-cols-2"><div className="rounded-2xl bg-[#F3E8D5] p-4"><p className="text-[10px] font-black uppercase tracking-[.15em] text-[#9A3F4A]">Where the family is</p><p className="mt-2 text-sm font-semibold">Following the evidence and deciding what matters next—not racing a weekly deadline.</p></div><div className="rounded-2xl bg-[#E7EFE5] p-4"><p className="text-[10px] font-black uppercase tracking-[.15em] text-[#2F6542]">Suggested next move</p><p className="mt-2 text-sm font-semibold">{investigation.next_action || investigation.success_criteria?.[0] || 'Compare what everyone noticed and choose the next useful question together.'}</p></div></div></> : <><h2 className="mt-4 text-3xl font-bold" style={{ fontFamily: 'var(--font-emilys-candy), cursive' }}>The next shared question is still emerging</h2><p className="mt-3 max-w-2xl text-sm leading-6 text-[#2F4731]/65">It may narrow, widen, branch, pause, or continue as long as the evidence calls for.</p></>}</div><aside className="border-t border-[#DCCFB9] bg-[#5B314E] p-6 text-white sm:p-8 lg:border-l lg:border-t-0"><p className="text-xs font-black uppercase tracking-[.18em] text-[#F0BE62]">Recent discoveries</p><div className="mt-5 space-y-4">{dashboard.recent_activity.slice(0, 4).map((activity) => <div key={`${activity.student_id}-${activity.lesson_id}-${activity.completed_at}`} className="border-b border-white/15 pb-4 last:border-0"><p className="font-bold">{activity.student_name}</p><p className="mt-1 text-sm leading-5 text-white/70">Added evidence: {activity.title}</p></div>)}{dashboard.recent_activity.length === 0 && <p className="text-sm leading-6 text-white/65">The family&rsquo;s first discoveries will appear here as learners add evidence and reflections.</p>}</div><p className="mt-6 text-xs leading-5 text-white/55">Investigations continue until the family finishes, changes direction, or finds a better question.</p></aside></div></section>

          <section><div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between"><div><p className="text-xs font-black uppercase tracking-[.18em] text-[#BD6809]">Each child&rsquo;s learning</p><h2 className="mt-1 text-3xl font-bold" style={{ fontFamily: 'var(--font-emilys-candy), cursive' }}>One family, distinct learners</h2><p className="mt-2 text-sm text-[#2F4731]/62">No impersonating children. Choose one only when you want details.</p></div><div className="flex gap-2"><button onClick={() => setShowClaimStudent(true)} className="inline-flex items-center gap-2 rounded-xl border border-[#CFC1A8] bg-white px-4 py-2.5 text-xs font-bold"><Link2 className="h-4 w-4" /> Connect learner</button><button onClick={() => setShowAddStudent(true)} className="inline-flex items-center gap-2 rounded-xl bg-[#BD6809] px-4 py-2.5 text-xs font-bold text-white"><Plus className="h-4 w-4" /> Create learner</button></div></div><div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">{dashboard.students.map((student) => <ChildCard key={student.student_id} student={student} onSelect={() => setSelectedStudentId(student.student_id)} />)}</div></section>

          {selectedStudent && <ChildOverview student={selectedStudent} portfolio={portfolio} portfolioLoading={portfolioLoading} onClose={() => setSelectedStudentId(null)} />}
          <ParentAdelinePanel />

          <div className="grid gap-5 lg:grid-cols-2"><section className="rounded-[26px] border border-[#D4C3A7] bg-[#FFFDF7] p-6"><div className="flex items-start gap-4"><div className="rounded-2xl bg-[#E7EFE5] p-3"><Compass className="h-5 w-5 text-[#2F6542]" /></div><div><p className="text-xs font-black uppercase tracking-[.14em] text-[#2F6542]">Parent Resource Vault</p><h2 className="mt-1 text-2xl font-bold">Browse with intention</h2><p className="mt-2 text-sm leading-6 text-[#2F4731]/62">Explore primary sources, experiments, museums, books, coding tools, games, arts-integrated projects, and family activities.</p><Link href="/dashboard/parent/resources" className="mt-4 inline-flex items-center gap-2 text-sm font-black text-[#9A3F4A]">Open the Resource Vault <ExternalLink className="h-4 w-4" /></Link></div></div></section><section className="rounded-[26px] border border-[#D4C3A7] bg-[#FFFDF7] p-6"><div className="flex items-start gap-4"><div className="rounded-2xl bg-[#F3E8D5] p-3"><Link2 className="h-5 w-5 text-[#BD6809]" /></div><div><p className="text-xs font-black uppercase tracking-[.14em] text-[#BD6809]">Family connections</p><h2 className="mt-1 text-2xl font-bold">Keep every learner&rsquo;s history</h2><p className="mt-2 text-sm leading-6 text-[#2F4731]/62">Create a learner from the parent account or connect an existing learner by invitation. Linking never requires recreating the student.</p><button onClick={() => setShowClaimStudent(true)} className="mt-4 inline-flex items-center gap-2 text-sm font-black text-[#9A3F4A]">Connect existing learner <ArrowRight className="h-4 w-4" /></button></div></div></section></div>
        </>}
      </div>
      {showAddStudent && <AddStudentDialog onClose={() => setShowAddStudent(false)} onAdd={handleAddStudent} />}
      {showClaimStudent && <ClaimStudentDialog onClose={() => setShowClaimStudent(false)} onClaimed={fetchData} />}
    </main>
  );
}
