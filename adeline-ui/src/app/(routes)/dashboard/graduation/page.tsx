'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { ArrowLeft, Check, GraduationCap, Loader2, Sparkles } from 'lucide-react';
import { getCreditDashboard, getOSRHEProgress } from '@/lib/brain-client';
import type { CreditDashboard, OSRHEProgress } from '@/lib/brain-client';
import { useStudent } from '@/lib/useStudent';

export default function GraduationPage() {
  const { student, loading } = useStudent();
  const [credits, setCredits] = useState<CreditDashboard | null>(null);
  const [requirements, setRequirements] = useState<OSRHEProgress | null>(null);
  const [dataLoading, setDataLoading] = useState(true);

  useEffect(() => {
    if (!student) return;
    setDataLoading(true);
    Promise.allSettled([
      getCreditDashboard(student.id),
      getOSRHEProgress(student.id),
    ]).then(([creditResult, requirementResult]) => {
      if (creditResult.status === 'fulfilled') setCredits(creditResult.value);
      if (requirementResult.status === 'fulfilled') setRequirements(requirementResult.value);
    }).finally(() => setDataLoading(false));
  }, [student]);

  const totalEvidence = useMemo(() => credits?.buckets.reduce((sum, bucket) => sum + bucket.evidenceCount, 0) ?? 0, [credits]);
  const earned = requirements?.totalEarned ?? credits?.approvedCourses.length ?? 0;
  const required = requirements?.totalRequired ?? 23;
  const percent = required > 0 ? Math.min(100, Math.round((earned / required) * 100)) : 0;

  if (loading || dataLoading) {
    return <div className="flex min-h-screen items-center justify-center bg-[#f4eddf] text-[#244a35]"><Loader2 className="h-5 w-5 animate-spin" /></div>;
  }

  return (
    <main className="min-h-screen bg-[#f4eddf] px-4 py-6 text-[#2d4333] sm:px-8">
      <div className="mx-auto max-w-6xl">
        <Link href="/dashboard" className="inline-flex items-center gap-1 text-xs text-[#746851] hover:text-[#244a35]"><ArrowLeft size={14} /> back to Adeline</Link>

        <header className="mt-5 grid gap-5 lg:grid-cols-[1fr_320px]">
          <div>
            <p className="text-[10px] uppercase tracking-[.22em] text-[#9a7b42]">the long road</p>
            <h1 className="mt-1 font-serif text-4xl text-[#244a35]">Graduation</h1>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-[#6f6759]">This is where Adeline translates real work, projects, lessons, reading, investigations, and saved evidence into a defensible academic record.</p>
          </div>
          <div className="rounded-[26px_17px_28px_20px] bg-[#254c37] p-5 text-[#fffaf0] shadow-lg">
            <GraduationCap size={22} className="text-[#dbb04a]" />
            <div className="mt-4 flex items-end justify-between gap-4"><span className="font-serif text-4xl">{percent}%</span><span className="pb-1 text-xs text-white/55">of listed requirements</span></div>
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/10"><div className="h-full rounded-full bg-[#d6a73c]" style={{ width: `${percent}%` }} /></div>
            <p className="mt-3 text-xs text-white/65">{earned.toFixed(1)} of {required.toFixed(1)} credits recognized</p>
          </div>
        </header>

        <section className="mt-8 grid gap-4 md:grid-cols-3">
          <Stat label="Evidence pieces" value={String(totalEvidence)} note="work Adeline can point to" jewel="#315f7b" />
          <Stat label="Courses formed" value={String(credits?.approvedCourses.length ?? 0)} note="approved from accumulated evidence" jewel="#8f4868" />
          <Stat label="Profile" value={credits?.currentProfile?.replaceAll('_', ' ') || 'Homeschool'} note="the rules currently being applied" jewel="#9d7825" />
        </section>

        <section className="mt-8 rounded-[28px_19px_30px_18px] border border-[#d1c4ad] bg-[#fffaf2] p-5 shadow-[0_8px_25px_rgba(70,52,32,.06)] sm:p-7">
          <div className="mb-6 flex items-start justify-between gap-4">
            <div><p className="text-[10px] uppercase tracking-[.18em] text-[#9a7b42]">requirements</p><h2 className="mt-1 font-serif text-2xl">What is filling up</h2></div>
            <Sparkles size={18} className="text-[#a47720]" />
          </div>

          {requirements?.buckets?.length ? (
            <div className="space-y-5">
              {requirements.buckets.map((bucket) => {
                const bucketPercent = bucket.required > 0 ? Math.min(100, Math.round((bucket.earned / bucket.required) * 100)) : 0;
                return <div key={bucket.bucket}>
                  <div className="mb-2 flex items-end justify-between gap-3"><div><h3 className="font-serif text-lg text-[#2b4b36]">{bucket.label}</h3><p className="text-[11px] text-[#847660]">{bucket.evidenceCount} evidence pieces · {bucket.hoursEarned.toFixed(1)} documented hours</p></div><p className="text-sm font-semibold text-[#775f2c]">{bucket.earned.toFixed(1)} / {bucket.required.toFixed(1)}</p></div>
                  <div className="h-2 overflow-hidden rounded-full bg-[#e7dfd0]"><div className="h-full rounded-full bg-[#42664c]" style={{ width: `${bucketPercent}%` }} /></div>
                </div>;
              })}
            </div>
          ) : (
            <p className="text-sm text-[#786d5c]">The requirement map has not loaded yet. Adeline can still collect evidence and form courses while that connection is being completed.</p>
          )}
        </section>

        {!!credits?.approvedCourses.length && (
          <section className="mt-8">
            <p className="text-[10px] uppercase tracking-[.18em] text-[#9a7b42]">already formed</p>
            <h2 className="mt-1 font-serif text-2xl">Courses that grew out of the work</h2>
            <div className="mt-4 grid gap-4 md:grid-cols-2">
              {credits.approvedCourses.map((course) => (
                <article key={course.proposalId} className="rounded-[20px_13px_22px_14px] border border-[#d2c5ae] bg-[#fffaf0] p-5">
                  <div className="flex items-start gap-3"><span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#e6f0e7] text-[#31553a]"><Check size={13} /></span><div><h3 className="font-serif text-lg text-[#294936]">{course.externalCourseName}</h3><p className="mt-1 text-xs text-[#766b58]">{course.hoursEarned.toFixed(1)} hours · {course.masteryGrade} mastery</p><p className="mt-2 text-[10px] uppercase tracking-[.12em] text-[#9a7a43]">{course.bucket.replaceAll('_', ' ')}</p></div></div>
                </article>
              ))}
            </div>
          </section>
        )}
      </div>
    </main>
  );
}

function Stat({ label, value, note, jewel }: { label: string; value: string; note: string; jewel: string }) {
  return <div className="rounded-[22px_15px_24px_17px] border border-[#d2c5ae] bg-[#fffaf0] p-5"><div className="mb-3 h-2.5 w-2.5 rounded-full" style={{ background: jewel, boxShadow: `0 0 12px ${jewel}55` }} /><p className="text-[10px] uppercase tracking-[.15em] text-[#88775f]">{label}</p><p className="mt-1 font-serif text-2xl capitalize text-[#2b4936]">{value}</p><p className="mt-1 text-xs text-[#7b6f5d]">{note}</p></div>;
}
