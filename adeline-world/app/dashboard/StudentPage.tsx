"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getPlayerSession, PlayerProfile } from "../lib/player-session";
import DashboardNav from "./DashboardNav";

type PageKind = "missions" | "journal" | "portfolio" | "skills" | "graduation";
type RecordItem = Record<string, unknown>;

const config: Record<PageKind, { title: string; eyebrow: string; intro: string; endpoint: (id: string) => string }> = {
  missions: { title: "My Missions", eyebrow: "WHAT’S READY NEXT", intro: "Adventures Adeline chose from your interests, growing skills, and natural next steps.", endpoint: (id) => `/api/brain/learning-plan/${id}?limit=12&include_all_tracks=true` },
  journal: { title: "My Journal", eyebrow: "YOUR LEARNING STORY", intro: "Lessons and discoveries you finished and sealed into your permanent learning record.", endpoint: (id) => `/api/brain/journal/recent/${id}?limit=50` },
  portfolio: { title: "My Portfolio", eyebrow: "MADE · BUILT · GROWN · PUBLISHED", intro: "The real work Adeline saves from your activities, lessons, and projects—not a pile of worksheets.", endpoint: (id) => `/api/brain/activities/${id}` },
  skills: { title: "Skills & Credits", eyebrow: "WHAT YOU CAN ACTUALLY DO", intro: "Credit earned from demonstrated work, organized toward a clear academic record.", endpoint: (id) => `/api/brain/credits/${id}` },
  graduation: { title: "Graduation Path", eyebrow: "THE ROAD AHEAD", intro: "What is complete, what is growing, and what still needs attention before graduation.", endpoint: (id) => `/api/brain/transcripts/${id}/osrhe-progress` },
};

const trackNames: Record<string, string> = {
  CREATION_SCIENCE: "Creation Science", HEALTH_NATUROPATHY: "Health & Naturopathy", HOMESTEADING: "Food Systems & Stewardship",
  GOVERNMENT_ECONOMICS: "Government & Economics", JUSTICE_CHANGEMAKING: "Justice & Changemaking", DISCIPLESHIP: "Discipleship",
  TRUTH_HISTORY: "Truth-Based History", ENGLISH_LITERATURE: "English & Literature", APPLIED_MATHEMATICS: "Applied Mathematics", CREATIVE_ECONOMY: "Creative Economy",
};

function text(value: unknown, fallback = "") { return typeof value === "string" ? value : fallback; }
function number(value: unknown) { return typeof value === "number" ? value : Number(value) || 0; }

export default function StudentPage({ kind }: { kind: PageKind }) {
  const page = config[kind];
  const [player, setPlayer] = useState<PlayerProfile | null>(null);
  const [data, setData] = useState<RecordItem | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const session = getPlayerSession();
    if (!session) { window.location.assign("/sign-in"); return; }
    queueMicrotask(() => setPlayer(session.player));
    fetch(page.endpoint(session.studentId), { headers: { Authorization: `Bearer ${session.token}` }, cache: "no-store" })
      .then(async (response) => { if (!response.ok) throw new Error("This record could not be loaded yet."); return response.json(); })
      .then((payload) => setData(payload as RecordItem))
      .catch((cause) => setError(cause instanceof Error ? cause.message : "This record could not be loaded yet."))
      .finally(() => setLoading(false));
  }, [page]);

  const initials = player?.display_name ? player.display_name.split(/\s+/).map((part) => part[0]).join("").slice(0, 2).toUpperCase() : "DA";

  return (
    <main className="dashboard-page">
      <header className="dashboard-header"><Link href="/">Dear Adeline</Link><span>{page.title}</span><button type="button" aria-label="Learner profile">{initials}</button></header>
      <div className="dashboard-layout"><DashboardNav active={kind} />
        <section className="record-page">
          <header className="record-hero"><p>{page.eyebrow}</p><h1>{page.title}</h1><span>{page.intro}</span></header>
          {loading && <div className="record-state">Adeline is gathering your record…</div>}
          {error && <div className="record-state error">{error}<button type="button" onClick={() => window.location.reload()}>Try again</button></div>}
          {!loading && !error && data && <RecordContent kind={kind} data={data} />}
        </section>
      </div>
    </main>
  );
}

function RecordContent({ kind, data }: { kind: PageKind; data: RecordItem }) {
  if (kind === "portfolio") {
    const activities = Array.isArray(data.activities) ? data.activities as RecordItem[] : [];
    return <><div className="record-stats"><Stat value={activities.length} label="Accomplishments"/><Stat value={number(data.total_credits).toFixed(2)} label="Credits earned"/><Stat value={new Set(activities.map((a) => text(a.primary_track))).size} label="Active tracks"/></div>
      {activities.length ? <div className="record-grid">{activities.map((item, index) => <RecordCard key={text(item.activity_id, String(index))} title={text(item.course_title, "Learning accomplishment")} description={text(item.activity_description)} tag={trackNames[text(item.primary_track)] ?? text(item.primary_track, "Real-world learning")} meta={`${number(item.credit_hours).toFixed(3)} credits · ${formatDate(item.sealed_at)}`} icon="✦" />)}</div> : <Empty title="Your portfolio is waiting for its first accomplishment." text="Tell Adeline what you made, built, grew, published, practiced, or finished. She will connect the learning and save the evidence here."/>}</>;
  }
  if (kind === "missions") {
    const lessons = Array.isArray(data.suggestions) ? data.suggestions as RecordItem[] : [];
    const projects = Array.isArray(data.projects) ? data.projects as RecordItem[] : [];
    const all = [...lessons.map((x) => ({...x, _type: "Lesson mission"})), ...projects.map((x) => ({...x, _type: "Project mission"}))];
    return all.length ? <div className="record-grid">{all.map((item, index) => {
      const id = text(item.id, String(index));
      const title = text(item.title, "New mission");
      const description = text(item.description, text(item.tagline));
      const track = text(item.track);
      const missionType = text(item._type).startsWith("Project") ? "project" : "lesson";
      const href = `/dashboard/missions/${encodeURIComponent(id)}?type=${missionType}&title=${encodeURIComponent(title)}&description=${encodeURIComponent(description)}&track=${encodeURIComponent(track)}`;
      return <RecordCard key={id} href={href} title={title} description={description} tag={text(item._type)} meta={`${trackNames[track] ?? track} · Open mission →`} icon={text(item.emoji, "✦")} />;
    })}</div> : <Empty title="No missions are queued yet." text="Talk with Adeline about what you want to learn or build, and she will shape the next missions around you."/>;
  }
  if (kind === "journal") {
    const entries = Array.isArray(data.entries) ? data.entries as RecordItem[] : [];
    return entries.length ? <div className="record-list">{entries.map((item, index) => <RecordCard key={`${text(item.lesson_id)}-${index}`} title={humanize(text(item.lesson_id, "Completed lesson"))} description={`${number(item.completed_blocks)} learning blocks completed`} tag={trackNames[text(item.track)] ?? humanize(text(item.track))} meta={formatDate(item.sealed_at)} icon="▤" />)}</div> : <Empty title="Your journal is ready for your first entry." text="Completed lessons and saved sketchnotes will live here in the order you experienced them."/>;
  }
  if (kind === "skills") {
    const buckets = Array.isArray(data.buckets) ? data.buckets as RecordItem[] : [];
    return buckets.length ? <div className="progress-list">{buckets.map((bucket, index) => { const hours = number(bucket.hoursEarned); const credit = number(bucket.creditEarned); return <article key={`${text(bucket.bucket)}-${index}`}><div><b>{humanize(text(bucket.bucket, "Learning area"))}</b><span>{hours.toFixed(1)} hours · {number(bucket.evidenceCount)} pieces of evidence</span></div><strong>{credit.toFixed(2)} credits</strong><i style={{width: `${Math.min(100, Math.max(4, credit * 100))}%`}} /></article>; })}</div> : <Empty title="Skills will appear as Adeline records evidence." text="This page counts demonstrated learning—not time spent clicking through screens."/>;
  }
  const buckets = Array.isArray(data.buckets) ? data.buckets as RecordItem[] : [];
  const earned = number(data.totalEarned), required = number(data.totalRequired);
  return <><div className="graduation-total"><div><b>{earned.toFixed(2)}</b><span>of {required || 23} credits earned</span></div><i><span style={{width: `${Math.min(100, required ? earned / required * 100 : 0)}%`}} /></i></div>{buckets.length ? <div className="progress-list">{buckets.map((bucket, index) => { const got = number(bucket.earned), need = number(bucket.required); return <article key={`${text(bucket.bucket)}-${index}`}><div><b>{text(bucket.label, humanize(text(bucket.bucket)))}</b><span>{got.toFixed(2)} of {need} credits</span></div><strong>{need ? Math.round(got / need * 100) : 0}%</strong><i style={{width: `${Math.min(100, need ? got / need * 100 : 0)}%`}} /></article>; })}</div> : <Empty title="Your graduation map is being prepared." text="As evidence becomes credit, each required area will fill in here."/>}</>;
}

function Stat({ value, label }: { value: string | number; label: string }) { return <article><b>{value}</b><span>{label}</span></article>; }
function RecordCard({ title, description, tag, meta, icon, href }: { title: string; description: string; tag: string; meta: string; icon: string; href?: string }) {
  const card = <article className="record-card"><b>{icon}</b><div><small>{tag}</small><h2>{title}</h2>{description && <p>{description}</p>}<span>{meta}</span></div></article>;
  return href ? <a className="record-card-link" href={href}>{card}</a> : card;
}
function Empty({ title, text: body }: { title: string; text: string }) { return <div className="record-empty"><b>🌱</b><h2>{title}</h2><p>{body}</p><a href="/dashboard#talk-to-adeline">Talk to Adeline →</a></div>; }
function humanize(value: string) { return value.replace(/[-_]+/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase()); }
function formatDate(value: unknown) { const raw = text(value); if (!raw) return "Saved to your record"; const date = new Date(raw); return Number.isNaN(date.getTime()) ? raw : date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }); }
