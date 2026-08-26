"use client";

import { useEffect, useState } from "react";
import { Archive, CheckCircle2, Download, ExternalLink, Gamepad2, Search, ShieldCheck } from "lucide-react";
import GenUIRenderer from "@/components/GenUIRenderer";
import { downloadInvestigationPrintable, sealJournal } from "@/lib/brain-client";
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

// ── Shared seal/print logic — identical for legacy and v11 rendering ──────────
// "Preserve the seal payload": both renderers call the same hook so the
// sealJournal() call is constructed by one code path regardless of which
// visual variant is showing. Only the JSX prompting reflection/artifact input
// differs between the two renderers; what gets sent to the backend does not.

function useLessonSeal(lesson: LessonResponse) {
  const [sealing, setSealing] = useState(false);
  const [sealed, setSealed] = useState(false);
  const [sealError, setSealError] = useState("");
  const [reflection, setReflection] = useState("");
  const [artifact, setArtifact] = useState("");
  const [learningStatus, setLearningStatus] = useState("");
  const [creditSealed, setCreditSealed] = useState(false);
  const [quizResults, setQuizResults] = useState<Array<{ correct: boolean; block_id?: string }>>([]);

  useEffect(() => {
    const collect = (event: Event) => {
      const detail = (event as CustomEvent<{ lessonId?: string; blockId?: string; correct?: boolean }>).detail;
      if (detail?.lessonId !== lesson.lesson_id || typeof detail.correct !== 'boolean') return;
      const correct = detail.correct;
      setQuizResults((current) => [
        ...current.filter((result) => result.block_id !== detail.blockId),
        { correct, block_id: detail.blockId },
      ]);
    };
    window.addEventListener('adeline:learning-evidence', collect);
    return () => window.removeEventListener('adeline:learning-evidence', collect);
  }, [lesson.lesson_id]);

  async function finishLesson(completedBlocks: number) {
    if (sealing || sealed) return;
    setSealing(true);
    setSealError("");
    try {
      const result = await sealJournal({
        lesson_id: lesson.lesson_id,
        plan_item_id: lesson.metadata?.printable_request?.plan_item_id,
        track: lesson.track,
        completed_blocks: completedBlocks,
        oas_standards: lesson.oas_standards.map(({ standard_id, text, grade }) => ({ standard_id, text, grade })),
        learner_reflection: reflection.trim(),
        concept_id: lesson.metadata?.concept_id,
        concept_name: lesson.metadata?.concept_name ?? lesson.title,
        quiz_results: quizResults,
        artifact_refs: artifact.trim() ? [`portfolio://investigation/${lesson.lesson_id}`] : [],
        evidence_sources: artifact.trim() ? [{ title: "Learner investigation artifact", url: `portfolio://investigation/${lesson.lesson_id}`, author: artifact.trim(), year: new Date().getFullYear() }] : [],
      });
      setLearningStatus(result.learning_status);
      setCreditSealed(result.credit_sealed);
      setSealed(true);
    } catch (reason) {
      setSealError(reason instanceof Error ? reason.message : "Adeline could not save this work yet.");
    } finally {
      setSealing(false);
    }
  }

  return {
    sealing, sealed, sealError, reflection, setReflection, artifact, setArtifact,
    learningStatus, creditSealed, finishLesson,
  };
}

function useDossierPrint(lesson: LessonResponse) {
  const [printing, setPrinting] = useState(false);
  const [printError, setPrintError] = useState("");
  async function printDossier() {
    if (!lesson.metadata?.printable_request || printing) return;
    setPrinting(true); setPrintError("");
    try { await downloadInvestigationPrintable(lesson.metadata.printable_request); }
    catch (reason) { setPrintError(reason instanceof Error ? reason.message : "The dossier could not be downloaded."); }
    finally { setPrinting(false); }
  }
  return { printing, printError, printDossier };
}

// ── v11 flow-aware rendering ────────────────────────────────────────────────
// experience_design.flow is the authored sequence/grouping authority for a
// v11 experience. It must never be re-sorted by experience_stage on the
// frontend — that is exactly the behavior this replaces. layout is advisory
// visual treatment only; unrecognized layouts still follow flow order, just
// with the neutral "default" treatment below.

type FlowNode = { node_id: string; label: string; block_ids: string[] };

export function isV11FlowExperience(lesson: LessonResponse): boolean {
  const formatVersion = lesson.blocks[0]?.canonical_format_version ?? 0;
  const flow = lesson.metadata?.experience_design?.flow;
  return formatVersion >= 11 && Array.isArray(flow) && flow.length > 0;
}

function resolveFlowGroups(blocks: LessonBlockResponse[], flow: FlowNode[]) {
  const byId = new Map(blocks.map((block) => [block.block_id, block]));
  return flow
    .map((node) => ({
      node,
      blocks: node.block_ids
        .map((id) => byId.get(id))
        .filter((block): block is LessonBlockResponse => !!block),
    }))
    .filter((group) => group.blocks.length > 0);
}

const LAYOUT_TREATMENTS: Record<string, { wrapper: string; label: string; group: string }> = {
  lab_notebook: {
    wrapper: "rounded-[24px] border border-[#0E7490]/40 bg-[#ECFEFF]/60 p-6 md:p-8",
    label: "mb-4 text-xs font-black uppercase tracking-[.16em] text-[#0E7490]",
    group: "grid gap-4 md:grid-cols-2 md:items-start",
  },
  dossier: {
    wrapper: "rounded-[24px] border-2 border-[#8B5E34] bg-[#FBF3E4] p-6 md:p-8",
    label: "mb-4 text-xs font-black uppercase tracking-[.16em] text-[#8B5E34]",
    group: "grid gap-4 md:grid-cols-2",
  },
  theology_map: {
    wrapper: "rounded-[24px] border-2 border-[#4338CA]/70 bg-[#F1F0FE] p-6 md:p-8",
    label: "mb-4 text-xs font-black uppercase tracking-[.16em] text-[#4338CA]",
    group: "grid gap-4 md:grid-cols-2",
  },
  skill_ladder: {
    wrapper: "rounded-2xl border border-[#D9CFBC] bg-white/70 p-5",
    label: "mb-3 text-xs font-black uppercase tracking-[.14em] text-[#BD6809]",
    group: "grid gap-3",
  },
  default: {
    wrapper: "rounded-2xl border border-[#D9CFBC]/70 bg-white/40 p-5 md:p-6",
    label: "mb-3 text-xs font-black uppercase tracking-[.14em] text-[#2F4731]/60",
    group: "grid gap-4",
  },
};

function FlowStep({
  node, blocks, layout, lessonId, studentId, isHomestead, agentName,
}: {
  node: FlowNode; blocks: LessonBlockResponse[]; layout: string;
  lessonId: string; studentId: string; isHomestead: boolean; agentName?: string;
}) {
  // A single-block step is one beat in the experience; a heavy bordered box
  // around one block is a rectangle around a rectangle, exactly what this
  // replaces. Grouping treatment is reserved for steps that actually group
  // multiple blocks, where a visible relationship needs to be communicated.
  if (blocks.length <= 1) {
    return (
      <section>
        {node.label && <p className="mb-3 text-xs font-black uppercase tracking-[.14em] text-[#2F4731]/55">{node.label}</p>}
        <GenUIRenderer lessonId={lessonId} blocks={blocks} isHomestead={isHomestead} oasStandards={[]} agentName={agentName} studentId={studentId} />
      </section>
    );
  }
  const treatment = LAYOUT_TREATMENTS[layout] ?? LAYOUT_TREATMENTS.default;
  return (
    <section className={treatment.wrapper}>
      {node.label && <p className={treatment.label}>{node.label}</p>}
      <div className={treatment.group}>
        {blocks.map((block) => (
          <GenUIRenderer key={block.block_id} lessonId={lessonId} blocks={[block]} isHomestead={isHomestead} oasStandards={[]} agentName={agentName} studentId={studentId} />
        ))}
      </div>
    </section>
  );
}

type LearnerContribution = NonNullable<NonNullable<LessonResponse["metadata"]>["learner_contribution"]>;

function SkillConnectionSummary({
  contribution,
  isIndividualSkill,
}: {
  contribution?: LearnerContribution;
  isIndividualSkill: boolean;
}) {
  return <>
    {!!contribution?.skill_connections?.length && <div className="mt-5 rounded-2xl border border-[#D9CFBC] bg-white p-4">
      <p className="text-xs font-black uppercase tracking-[.14em] text-[#BD6809]">{isIndividualSkill ? "Your current skill target" : "Woven into this shared question"}</p>
      <ul className="mt-3 grid gap-2 text-sm">
        {contribution.skill_connections.map((target) => <li key={`${target.domain}-${target.concept_id ?? target.standard_code ?? target.title}`}><b className="capitalize">{target.domain}:</b> {target.title} <span className="text-[#2F4731]/55">· working level {target.working_level ?? "current"}</span>{target.contribution_prompt && <span className="mt-1 block text-xs leading-5 text-[#2F4731]/65">{target.contribution_prompt}</span>}</li>)}
      </ul>
      {contribution.integration_rule && <p className="mt-3 text-xs leading-5 text-[#2F4731]/60">{contribution.integration_rule}</p>}
    </div>}
    {!!contribution?.separate_skill_targets?.length && <div className="mt-4 rounded-2xl border border-[#D9CFBC] bg-white/70 p-4">
      <p className="text-xs font-black uppercase tracking-[.14em] text-[#2F4731]/60">Kept in your separate skill path</p>
      <ul className="mt-2 grid gap-1 text-sm text-[#2F4731]/70">{contribution.separate_skill_targets.map((target) => <li key={`${target.domain}-${target.suggestion_id}`}><b className="capitalize">{target.domain}:</b> {target.title}—not forced into this theme.</li>)}</ul>
    </div>}
  </>;
}

function V11FlowExperience({ lesson, studentId }: { lesson: LessonResponse; studentId: string }) {
  const seal = useLessonSeal(lesson);
  const print = useDossierPrint(lesson);
  const visible = lesson.blocks.filter((block) => !block.is_silenced);
  const resources = visible.filter((block) => block.block_type === "RESOURCE_COLLECTION");
  const design = lesson.metadata?.experience_design ?? {};
  const flow = (design.flow ?? []) as FlowNode[];
  const layout = design.layout ?? "";
  const groups = resolveFlowGroups(visible, flow);
  const demonstrationContract = lesson.metadata?.demonstration_contract;
  const portfolioTask = lesson.metadata?.portfolio_task;
  const learnerContribution = lesson.metadata?.learner_contribution;
  const isIndividualSkill = lesson.metadata?.delivery_mode === "INDIVIDUAL_SKILL";

  const centralQuestion = design.central_question?.trim() || questionFrom(visible, lesson.title);
  const entryMove = design.entry_move?.trim();

  const artifactPrompt =
    learnerContribution?.artifact_prompt ||
    demonstrationContract?.artifact_prompt ||
    portfolioTask?.evidence_to_preserve ||
    "Describe, link, or identify the drawing, build, calculation, photo, recording, source analysis, or other work you want preserved.";
  const demonstrationPrompt =
    demonstrationContract?.invitation ||
    demonstrationContract?.learner_prompt ||
    "What did this experience help you understand?";

  return <article className="space-y-6 pb-20 text-[#2F4731]">
    <header className="overflow-hidden rounded-[30px] border border-[#D9CFBC] bg-[linear-gradient(135deg,#F5E6C8,#E3ECDD)] shadow-sm">
      <div className="grid gap-8 p-7 md:grid-cols-[1.2fr_.8fr] md:p-11">
        <div>
          <p className="text-xs font-black uppercase tracking-[.2em] text-[#A95322]">{isIndividualSkill ? "Your skill practice" : "Today’s family investigation"}</p>
          <h1 className="mt-3 text-5xl leading-[.95] md:text-6xl" style={{ fontFamily: "var(--font-emilys-candy), cursive" }}>{lesson.title}</h1>
          <p className="mt-5 max-w-2xl text-base leading-7 text-[#2F4731]/75">{entryMove || (isIndividualSkill ? "Work at your current level. Practice the skill, show your reasoning, and leave evidence of what you can do." : "Follow the shared question. Use what helps. Make, test, examine, or decide something real.")}</p>
          {lesson.metadata?.printable_request && <button type="button" onClick={() => void print.printDossier()} disabled={print.printing} className="mt-5 inline-flex min-h-11 items-center gap-2 rounded-xl border border-[#2F4731] bg-white/70 px-4 py-2 text-sm font-bold disabled:opacity-50"><Download className="h-4 w-4" />{print.printing ? "Preparing dossier…" : isIndividualSkill ? "Print skill practice" : "Print field dossier"}</button>}
          {print.printError && <p className="mt-2 text-sm font-semibold text-red-700">{print.printError}</p>}
        </div>
        <div className="self-center border-l-4 border-[#BD6809] pl-6">
          <p className="text-xs font-black uppercase tracking-[.16em] text-[#BD6809]">The question worth following</p>
          <p className="mt-3 text-2xl leading-snug" style={{ fontFamily: "var(--font-kalam), cursive" }}>{centralQuestion}</p>
        </div>
      </div>
    </header>

    {groups.map(({ node, blocks }) => (
      <FlowStep
        key={node.node_id}
        node={node}
        blocks={blocks}
        layout={layout}
        lessonId={lesson.lesson_id}
        studentId={studentId}
        isHomestead={lesson.track === "HOMESTEADING"}
        agentName={lesson.agent_name}
      />
    ))}

    {resources.map((block) => <ResourceCollection key={block.block_id} block={block} />)}

    <section className="rounded-[26px] border-2 border-[#BD6809] bg-[#FDF6E9] p-6 md:p-8">
      {seal.sealed ? (
        <>
          <CheckCircle2 className="h-9 w-9 text-[#4F7A58]" />
          <h2 className="mt-3 text-2xl font-bold">Saved to your learning record</h2>
          <p className="mt-2 text-sm text-[#2F4731]/65">
            This experience is recorded as {seal.learningStatus.toLowerCase().replaceAll("_", " ")}.{" "}
            {seal.creditSealed ? "The demonstrated work also earned traceable credit." : "It did not automatically award mastery or credit; Adeline will use later demonstrations and review to update the concept."}
          </p>
        </>
      ) : (
        <>
          <p className="text-xs font-black uppercase tracking-[.18em] text-[#BD6809]">Preserve what you found</p>
          <h2 className="mt-2 text-3xl" style={{ fontFamily: "var(--font-emilys-candy), cursive" }}>{demonstrationPrompt}</h2>
          {learnerContribution?.role && <p className="mt-3 max-w-3xl text-base font-bold leading-7">{learnerContribution.role}</p>}
          <SkillConnectionSummary contribution={learnerContribution} isIndividualSkill={isIndividualSkill} />
          {(learnerContribution?.success_criteria?.length || demonstrationContract?.success_criteria?.length) ? (
            <ul className="mt-4 grid gap-2 text-sm">
              {(learnerContribution?.success_criteria || demonstrationContract?.success_criteria || []).map((criterion) => (
                <li key={criterion} className="flex gap-2"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-[#4F7A58]" />{criterion}</li>
              ))}
            </ul>
          ) : null}
          <label className="mt-5 grid gap-2 text-sm font-bold">
            <span>{artifactPrompt}</span>
            <textarea value={seal.artifact} onChange={(event) => seal.setArtifact(event.target.value)} rows={4} placeholder={isIndividualSkill ? "I solved… My reasoning was… The part I can now do is…" : "I made… My evidence shows… The link or file is… My part of the family investigation was…"} className="rounded-xl border border-[#BFB39E] bg-white p-3 font-normal" />
          </label>
          <label className="mt-4 grid gap-2 text-sm font-bold">
            <span>{demonstrationContract?.learner_prompt || "Explain what the evidence shows and how you know."}</span>
            <textarea value={seal.reflection} onChange={(event) => seal.setReflection(event.target.value)} rows={3} minLength={20} placeholder="I noticed… I tested… The result changed my thinking because…" className="rounded-xl border border-[#BFB39E] bg-white p-3 font-normal" />
          </label>
          <button type="button" onClick={() => void seal.finishLesson(visible.length)} disabled={seal.sealing || seal.reflection.trim().length < 20} className="mt-5 rounded-xl bg-[#2F4731] px-6 py-3 text-sm font-bold text-white disabled:opacity-50">{seal.sealing ? "Saving…" : "Save this evidence"}</button>
        </>
      )}
      {seal.sealError && <p className="mt-3 text-sm font-semibold text-red-700" role="alert">{seal.sealError}</p>}
    </section>
  </article>;
}

// ── Legacy stage-bucketed rendering — unchanged behavior ───────────────────
// Every pre-v11 canonical (no experience_design.flow) continues through this
// exact path. Do not alter its output.

function LegacyStageExperience({ lesson, studentId }: { lesson: LessonResponse; studentId: string }) {
  const seal = useLessonSeal(lesson);
  const print = useDossierPrint(lesson);
  const visible = lesson.blocks.filter((block) => !block.is_silenced);
  const resources = visible.filter((block) => block.block_type === "RESOURCE_COLLECTION");
  const teaching = visible.filter((block) => block.block_type !== "RESOURCE_COLLECTION");
  const byStage = (stage: LessonBlockResponse['experience_stage']) => teaching.filter((block) => block.experience_stage === stage);
  const invitation = byStage('INVITATION');
  const discovery = byStage('DISCOVERY');
  const action = [...byStage('ACTION'), ...byStage('CREATION')];
  const demonstration = byStage('DEMONSTRATION');
  const reflectionBlocks = byStage('REFLECTION');
  // Compatibility for an old canonical during cache turnover. Version 6
  // canonicals arrive with explicit semantic stages from the Brain.
  const unstaged = teaching.filter((block) => !block.experience_stage);

  const render = (blocks: LessonBlockResponse[]) => blocks.length ? <GenUIRenderer lessonId={lesson.lesson_id} blocks={blocks} isHomestead={lesson.track === "HOMESTEADING"} oasStandards={[]} agentName={lesson.agent_name} studentId={studentId} /> : null;

  const demonstrationContract = lesson.metadata?.demonstration_contract;
  const learnerContribution = lesson.metadata?.learner_contribution;
  const isIndividualSkill = lesson.metadata?.delivery_mode === "INDIVIDUAL_SKILL";

  return <article className="space-y-6 pb-20 text-[#2F4731]">
    <header className="overflow-hidden rounded-[30px] border border-[#D9CFBC] bg-[linear-gradient(135deg,#F5E6C8,#E3ECDD)] shadow-sm">
      <div className="grid gap-8 p-7 md:grid-cols-[1.2fr_.8fr] md:p-11">
        <div><p className="text-xs font-black uppercase tracking-[.2em] text-[#A95322]">{isIndividualSkill ? "Your skill practice" : "Today’s family investigation"}</p><h1 className="mt-3 text-5xl leading-[.95] md:text-6xl" style={{ fontFamily: "var(--font-emilys-candy), cursive" }}>{lesson.title}</h1><p className="mt-5 max-w-2xl text-base leading-7 text-[#2F4731]/75">{isIndividualSkill ? "Work at your current level. Practice the skill, show your reasoning, and leave evidence of what you can do." : "Follow the shared question. Use what helps. Make, test, examine, or decide something real."}</p>{lesson.metadata?.printable_request && <button type="button" onClick={() => void print.printDossier()} disabled={print.printing} className="mt-5 inline-flex min-h-11 items-center gap-2 rounded-xl border border-[#2F4731] bg-white/70 px-4 py-2 text-sm font-bold disabled:opacity-50"><Download className="h-4 w-4" />{print.printing ? "Preparing dossier…" : isIndividualSkill ? "Print skill practice" : "Print field dossier"}</button>}{print.printError && <p className="mt-2 text-sm font-semibold text-red-700">{print.printError}</p>}</div>
        <div className="self-center border-l-4 border-[#BD6809] pl-6"><p className="text-xs font-black uppercase tracking-[.16em] text-[#BD6809]">The question worth following</p><p className="mt-3 text-2xl leading-snug" style={{ fontFamily: "var(--font-kalam), cursive" }}>{questionFrom(teaching, lesson.title)}</p></div>
      </div>
    </header>

    {invitation.length > 0 && <section>{render(invitation)}</section>}
    {discovery.length > 0 && <section><p className="mb-4 text-xs font-black uppercase tracking-[.16em] text-[#BD6809]">Clues and tools</p>{render(discovery)}</section>}
    {action.length > 0 && <section><p className="text-xs font-black uppercase tracking-[.16em] text-[#BD6809]">Do something with it</p><h2 className="mt-2 mb-6 text-3xl" style={{ fontFamily: "var(--font-emilys-candy), cursive" }}>Investigate, make, test, or decide</h2>{render(action)}</section>}
    {resources.map((block) => <ResourceCollection key={block.block_id} block={block} />)}
    {demonstration.length > 0 && <section className="border-y-2 border-[#2F4731] py-8"><p className="text-xs font-black uppercase tracking-[.18em] text-[#BD6809]">Demonstrate</p><h2 className="mt-2 mb-6 text-4xl" style={{ fontFamily: "var(--font-emilys-candy), cursive" }}>Show what the experience helped you understand</h2>{render(demonstration)}</section>}
    <section className="rounded-[26px] border-2 border-[#BD6809] bg-[#FDF6E9] p-6 md:p-8">
      <p className="text-xs font-black uppercase tracking-[.18em] text-[#BD6809]">Your contribution</p>
      <h2 className="mt-2 text-3xl" style={{ fontFamily: "var(--font-emilys-candy), cursive" }}>{demonstrationContract?.invitation || "Leave evidence of what you discovered"}</h2>
      {learnerContribution?.role && <p className="mt-3 max-w-3xl text-base font-bold leading-7">{learnerContribution.role}</p>}
      {learnerContribution?.prompt && learnerContribution.prompt !== learnerContribution.role && <p className="mt-2 max-w-3xl text-sm leading-6">{learnerContribution.prompt}</p>}
      <SkillConnectionSummary contribution={learnerContribution} isIndividualSkill={isIndividualSkill} />
      <p className="mt-3 max-w-3xl text-sm leading-6 text-[#2F4731]/70">{learnerContribution?.artifact_prompt || demonstrationContract?.artifact_prompt || lesson.metadata?.portfolio_task?.evidence_to_preserve || "Describe, link, or identify the drawing, build, calculation, photo, recording, source analysis, or other work you want preserved."}</p>
      {(learnerContribution?.success_criteria?.length || demonstrationContract?.success_criteria?.length) ? <ul className="mt-4 grid gap-2 text-sm">{(learnerContribution?.success_criteria || demonstrationContract?.success_criteria || []).map((criterion) => <li key={criterion} className="flex gap-2"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-[#4F7A58]" />{criterion}</li>)}</ul> : null}
      <label className="mt-5 grid gap-2 text-sm font-bold"><span>What should Adeline preserve in your portfolio?</span><textarea value={seal.artifact} onChange={(event) => seal.setArtifact(event.target.value)} rows={4} placeholder={isIndividualSkill ? "I solved… My reasoning was… The part I can now do is…" : "I made… My evidence shows… The link or file is… My part of the family investigation was…"} className="rounded-xl border border-[#BFB39E] bg-white p-3 font-normal" /></label>
    </section>
    {reflectionBlocks.length > 0 && <section>{render(reflectionBlocks)}</section>}
    {unstaged.length > 0 && <section>{render(unstaged)}</section>}
    <section className="rounded-[26px] border border-[#D9CFBC] bg-[#F0FDF4] p-6 text-center md:p-8">
      {seal.sealed ? <><CheckCircle2 className="mx-auto h-9 w-9 text-[#4F7A58]" /><h2 className="mt-3 text-2xl font-bold">Saved to your learning record</h2><p className="mt-2 text-sm text-[#2F4731]/65">This experience is recorded as {seal.learningStatus.toLowerCase().replaceAll("_", " ")}. {seal.creditSealed ? "The demonstrated work also earned traceable credit." : "It did not automatically award mastery or credit; Adeline will use later demonstrations and review to update the concept."}</p></> : <><h2 className="text-2xl font-bold">What changed in your thinking?</h2><p className="mx-auto mt-2 max-w-xl text-sm leading-6 text-[#2F4731]/65">Tell Adeline what you noticed, made, tested, decided, or can now explain. This records the experience. Mastery and credit require a scored demonstration, artifact, or reviewed observation.</p><label className="mx-auto mt-5 grid max-w-2xl gap-2 text-left text-sm font-bold"><span>Your field note</span><textarea value={seal.reflection} onChange={(event) => seal.setReflection(event.target.value)} rows={4} minLength={20} placeholder="I noticed… I tested… The result changed my thinking because…" className="rounded-xl border border-[#BFB39E] bg-white p-3 font-normal" /></label><button type="button" onClick={() => void seal.finishLesson(visible.length)} disabled={seal.sealing || seal.reflection.trim().length < 20} className="mt-5 rounded-xl bg-[#2F4731] px-6 py-3 text-sm font-bold text-white disabled:opacity-50">{seal.sealing ? "Saving…" : "Save this field note"}</button></>}
      {seal.sealError && <p className="mt-3 text-sm font-semibold text-red-700" role="alert">{seal.sealError}</p>}
    </section>
  </article>;
}

// ── Dispatch — no hooks here; each branch owns its own ─────────────────────

export default function FamilyCanonicalLesson({ lesson, studentId }: { lesson: LessonResponse; studentId: string }) {
  if (isV11FlowExperience(lesson)) {
    return <V11FlowExperience lesson={lesson} studentId={studentId} />;
  }
  return <LegacyStageExperience lesson={lesson} studentId={studentId} />;
}
