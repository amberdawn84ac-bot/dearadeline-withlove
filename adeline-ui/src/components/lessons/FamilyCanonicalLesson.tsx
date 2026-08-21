"use client";

import { useState } from "react";
import { Archive, CheckCircle2, ExternalLink, Gamepad2, Search, ShieldCheck, Sparkles, Users } from "lucide-react";
import GenUIRenderer from "@/components/GenUIRenderer";
import { sealJournal } from "@/lib/brain-client";
import type { LessonBlockResponse, LessonResponse } from "@/lib/brain-client";

type Resource = {
  id?: string; title?: string; provider?: string; resource_type?: string;
  source_url?: string; description?: string; use_mode?: string; license?: string;
  game_mode?: string; estimated_minutes?: number; discovery_prompt?: string;
  mastery_prompt?: string; portfolio_output?: string; skills_practiced?: string[];
};

function resourcesFrom(block: LessonBlockResponse): Resource[] {
  const value = block.metadata?.resources;
  return Array.isArray(value) ? value.filter((item): item is Resource => !!item && typeof item === "object") : [];
}

function role(blocks: LessonBlockResponse[], key: "elementary" | "middle" | "high_school", fallback: string) {
  return blocks.find((block) => block.family_roles?.[key])?.family_roles?.[key] ?? fallback;
}

function questionFrom(blocks: LessonBlockResponse[], title: string) {
  const first = blocks.find((block) => block.content.trim())?.content ?? "";
  const match = first.match(/(?:^|\n)([^\n?]{18,180}\?)/);
  return match?.[1]?.replace(/^#+\s*/, "") ?? `What changes when your family investigates ${title.toLowerCase()} for yourselves?`;
}

function ResourceCollection({ block }: { block: LessonBlockResponse }) {
  const resources = resourcesFrom(block);
  if (!resources.length) return null;
  return (
    <section className="rounded-[26px] border border-[#D9CFBC] bg-[#F0FDF4] p-6 md:p-8" aria-labelledby={`resource-${block.block_id}`}>
      <div className="flex items-center gap-3"><Archive className="h-6 w-6 text-[#BD6809]" /><h2 id={`resource-${block.block_id}`} className="text-3xl" style={{ fontFamily: "var(--font-emilys-candy), cursive" }}>{block.title ?? "Explore the real thing"}</h2></div>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-[#2F4731]/70">{block.content}</p>
      <div className="mt-6 grid gap-4 md:grid-cols-2">
        {resources.map((resource, index) => (
          <article key={resource.id ?? index} className="flex flex-col rounded-2xl border border-[#D9CFBC] bg-white p-5">
            <div className="flex items-center justify-between gap-3">
              <span className="text-xs font-black uppercase tracking-wider text-[#BD6809]">{resource.provider}</span>
              <span className="rounded-full bg-[#FDF6E9] px-3 py-1 text-[11px] font-bold">{resource.game_mode ?? resource.resource_type?.replaceAll("_", " ")}</span>
            </div>
            <h3 className="mt-3 text-lg font-bold">{resource.title}</h3>
            <p className="mt-2 flex-1 text-sm leading-6 text-[#2F4731]/65">{resource.description}</p>
            {resource.discovery_prompt && <div className="mt-4 rounded-xl bg-[#FDF6E9] p-3 text-sm"><b>Start by noticing:</b> {resource.discovery_prompt}</div>}
            <div className="mt-4 flex flex-wrap items-center gap-2 text-xs text-[#2F4731]/60">
              <ShieldCheck className="h-4 w-4" /><span>{resource.use_mode ?? "LINK"}</span><span>·</span><span>{resource.license ?? "Check item rights"}</span>{resource.estimated_minutes ? <><span>·</span><span>~{resource.estimated_minutes} min</span></> : null}
            </div>
            {resource.source_url && <a href={resource.source_url} target="_blank" rel="noopener noreferrer" className="mt-4 inline-flex min-h-11 items-center justify-center gap-2 rounded-xl bg-[#2F4731] px-4 py-2 text-sm font-bold text-white">{resource.resource_type?.includes("GAME") ? <Gamepad2 className="h-4 w-4" /> : <Search className="h-4 w-4" />} Open resource <ExternalLink className="h-4 w-4" /></a>}
            {resource.portfolio_output && <p className="mt-3 text-xs leading-5 text-[#2F4731]/55"><b>Bring back:</b> {resource.portfolio_output}</p>}
          </article>
        ))}
      </div>
      <p className="mt-5 text-xs leading-5 text-[#2F4731]/55">Outside resources provide evidence and experiences. Adeline supplies the lesson. Rights are checked conservatively: unknown means link, never copy.</p>
    </section>
  );
}

export default function FamilyCanonicalLesson({ lesson, studentId }: { lesson: LessonResponse; studentId: string }) {
  const [sealing, setSealing] = useState(false);
  const [sealed, setSealed] = useState(false);
  const [sealError, setSealError] = useState("");
  const visible = lesson.blocks.filter((block) => !block.is_silenced);
  const resources = visible.filter((block) => block.block_type === "RESOURCE_COLLECTION");
  const teaching = visible.filter((block) => block.block_type !== "RESOURCE_COLLECTION");
  const actionTypes = new Set(["LAB_MISSION", "EXPERIMENT", "REAL_WORLD_APP", "SIMULATION", "PROJECT_BUILDER"]);
  const masteryTypes = new Set(["QUIZ", "FLASHCARD", "GENUI_ASSEMBLY", "SCAFFOLDED_PROBLEM"]);
  const investigation = teaching.filter((block) => actionTypes.has(block.block_type));
  const mastery = teaching.filter((block) => masteryTypes.has(block.block_type));
  const knowledge = teaching.filter((block) => !actionTypes.has(block.block_type) && !masteryTypes.has(block.block_type));

  const render = (blocks: LessonBlockResponse[]) => blocks.length ? <GenUIRenderer lessonId={lesson.lesson_id} blocks={blocks} isHomestead={lesson.track === "HOMESTEADING"} oasStandards={[]} agentName={lesson.agent_name} studentId={studentId} /> : null;

  async function finishLesson() {
    if (sealing || sealed) return;
    setSealing(true);
    setSealError("");
    try {
      await sealJournal({
        lesson_id: lesson.lesson_id,
        track: lesson.track,
        completed_blocks: visible.length,
        oas_standards: lesson.oas_standards.map(({ standard_id, text, grade }) => ({ standard_id, text, grade })),
        credit_draft: lesson.credits_awarded[0],
      });
      setSealed(true);
    } catch (reason) {
      setSealError(reason instanceof Error ? reason.message : "Adeline could not save this work yet.");
    } finally {
      setSealing(false);
    }
  }

  return <article className="space-y-6 pb-20 text-[#2F4731]">
    <header className="overflow-hidden rounded-[30px] border border-[#D9CFBC] bg-[linear-gradient(135deg,#F5E6C8,#E3ECDD)] shadow-sm">
      <div className="grid gap-8 p-7 md:grid-cols-[1.2fr_.8fr] md:p-11">
        <div><p className="text-xs font-black uppercase tracking-[.2em] text-[#A95322]">One shared family lesson · {lesson.track.replaceAll("_", " ")}</p><h1 className="mt-3 text-5xl leading-[.95] md:text-6xl" style={{ fontFamily: "var(--font-emilys-candy), cursive" }}>{lesson.title}</h1><p className="mt-5 max-w-2xl text-base leading-7 text-[#2F4731]/75">Learn the truth together, investigate something real, demonstrate understanding, and preserve meaningful evidence.</p></div>
        <div className="rounded-[26px] border border-white/70 bg-white/70 p-6"><p className="text-xs font-black uppercase tracking-[.16em] text-[#BD6809]">The family question</p><p className="mt-3 text-2xl leading-snug" style={{ fontFamily: "var(--font-kalam), cursive" }}>{questionFrom(teaching, lesson.title)}</p></div>
      </div>
    </header>

    <section className="grid gap-4 md:grid-cols-3" aria-label="Family learning levels">
      {[
        ["Younger learners", role(teaching, "elementary", "Notice, identify, draw, retell, measure, or build.")],
        ["Middle learners", role(teaching, "middle", "Explain cause and effect, compare evidence, record results, and apply.")],
        ["Older learners", role(teaching, "high_school", "Evaluate sources, calculate, design, lead, and defend conclusions.")],
      ].map(([title, text], index) => <div key={title} className="rounded-2xl border border-[#E7DAC3] bg-white p-5"><div className="flex items-center gap-2 text-[#BD6809]"><Users className="h-4 w-4" /><span className="text-xs font-black uppercase tracking-wider">Layer {index + 1}</span></div><h2 className="mt-3 text-lg font-bold">{title}</h2><p className="mt-1 text-sm leading-6 text-[#2F4731]/65">{text}</p></div>)}
    </section>

    {knowledge.length > 0 && <section className="rounded-[26px] border border-[#E7DAC3] bg-[#FFFEF7] p-6 md:p-8"><div className="mb-6 flex items-center gap-3"><Sparkles className="h-6 w-6 text-[#BD6809]" /><h2 className="text-3xl" style={{ fontFamily: "var(--font-emilys-candy), cursive" }}>Learn enough to investigate well</h2></div>{render(knowledge)}</section>}
    {investigation.length > 0 && <section className="rounded-[26px] border border-[#E7DAC3] bg-white p-6 md:p-8"><p className="text-xs font-black uppercase tracking-[.16em] text-[#BD6809]">The shared investigation</p><h2 className="mt-2 mb-6 text-3xl" style={{ fontFamily: "var(--font-emilys-candy), cursive" }}>Try it in the real world</h2>{render(investigation)}</section>}
    {resources.map((block) => <ResourceCollection key={block.block_id} block={block} />)}
    {mastery.length > 0 && <section className="rounded-[30px] border-2 border-[#2F4731] bg-[#FFFEF7] p-6 md:p-9"><p className="text-xs font-black uppercase tracking-[.18em] text-[#BD6809]">Interactive finish</p><h2 className="mt-2 mb-6 text-4xl" style={{ fontFamily: "var(--font-emilys-candy), cursive" }}>Show what you understand</h2>{render(mastery)}</section>}
    <section className="rounded-[26px] border border-[#D9CFBC] bg-[#F0FDF4] p-6 text-center md:p-8">
      {sealed ? <><CheckCircle2 className="mx-auto h-9 w-9 text-[#4F7A58]" /><h2 className="mt-3 text-2xl font-bold">Saved to your learning record</h2><p className="mt-2 text-sm text-[#2F4731]/65">Adeline updated what you have demonstrated and will use it to choose what comes next.</p></> : <><h2 className="text-2xl font-bold">Finished this experience?</h2><p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-[#2F4731]/65">Save the work only after you have completed the investigation and the interactive finish. Your concepts, evidence, and any earned credit stay private in the learning record.</p><button type="button" onClick={() => void finishLesson()} disabled={sealing} className="mt-5 rounded-xl bg-[#2F4731] px-6 py-3 text-sm font-bold text-white disabled:opacity-50">{sealing ? "Saving…" : "Save what I learned"}</button></>}
      {sealError && <p className="mt-3 text-sm font-semibold text-red-700" role="alert">{sealError}</p>}
    </section>
  </article>;
}
