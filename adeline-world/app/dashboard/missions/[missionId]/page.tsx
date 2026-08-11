"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import DashboardNav from "../../DashboardNav";
import { getPlayerSession, PlayerProfile } from "../../../lib/player-session";

type Item = Record<string, unknown>;
type Scene = { sceneTitle?: { text?: string }; narration?: string; teachingLayer?: Item; blockType?: string };
type AnimatedLesson = {
  title?: { text?: string };
  learningGoals?: string[];
  scenes?: Scene[];
  vocabulary?: Item[];
  assessment?: Item[];
  extensionActivities?: Item[];
};
type MissionQuery = { type: string; title: string; description: string; track: string };
type PlayerSession = NonNullable<ReturnType<typeof getPlayerSession>>;
function asText(value: unknown, fallback = "") { return typeof value === "string" || typeof value === "number" ? String(value) : fallback; }
function asList(value: unknown) { return Array.isArray(value) ? value : []; }

function blockToScene(block: Item, index: number): Scene {
  const kind = asText(block.block_type, "LESSON").replaceAll("_", " ");
  const title = asText(block.title, kind.toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase()));
  return {
    blockType: asText(block.block_type, "NARRATIVE"),
    sceneTitle: { text: title || `Lesson part ${index + 1}` },
    narration: asText(block.content, "This lesson block is being prepared."),
    teachingLayer: block.teachingLayer && typeof block.teachingLayer === "object" ? block.teachingLayer as Item : {},
  };
}

function childrenWhoChangedHistory(): AnimatedLesson {
  return {
    title: { text: "Children Who Changed History" },
    learningGoals: [
      "Describe how young people have changed laws, public opinion, education, and human rights.",
      "Compare the courage, strategies, and lasting impact of five young changemakers.",
      "Explain why history sometimes celebrates one person while nearly forgetting another.",
    ],
    scenes: [
      {
        sceneTitle: { text: "History has never belonged only to adults" },
        narration: "Children are often described as the people who will change the future. History shows something stronger: children have already changed their own present. They challenged segregation, invented a new reading system, confronted fear between nations, and forced adults to face injustice.",
        teachingLayer: {
          visualSummary: [
            { text: "A child can recognize an injustice before having the legal power to fix it." },
            { text: "Change usually requires courage plus a useful action: refusing, writing, creating, speaking, or enduring." },
            { text: "Young changemakers rarely acted alone; families, teachers, lawyers, journalists, and communities helped turn courage into lasting change." },
          ],
          whyItMatters: { text: "Age affects a person's power, but it does not erase their insight, responsibility, or ability to influence the world." },
          activity: { text: "As you meet each person, keep three sketchnote symbols: the barrier they faced, the action they took, and the change that followed." },
        },
      },
      {
        sceneTitle: { text: "Louis Braille: turning darkness into language" },
        narration: "Louis Braille was born in France in 1809 and lost his sight after a childhood accident. At school, the few raised-letter books available to blind students were enormous and slow to read. At age twelve, Louis learned about a military code of raised dots called “night writing.” He simplified and rebuilt the idea. By age fifteen, in 1824, he had developed the six-dot system that became braille.",
        teachingLayer: {
          visualSummary: [
            { text: "Problem: blind readers had very few practical books and could not easily write for themselves." },
            { text: "Action: Louis redesigned a twelve-dot military code into compact six-dot cells readable by touch." },
            { text: "Impact: braille gave blind people a powerful way to read, write, study music, and participate independently." },
          ],
          deepExplanation: { text: "Braille was not immediately accepted by authorities. The school where Louis taught officially adopted it only after his death. A good invention can be resisted when institutions are attached to familiar methods—even when the people using the new method know it works better." },
          activity: { text: "Feel the logic: a braille cell has six possible dot positions. Sketch a 2-by-3 cell and invent three tactile symbols. What makes a symbol easy or difficult to distinguish by touch?" },
        },
      },
      {
        sceneTitle: { text: "Claudette Colvin: nine months before Rosa Parks" },
        narration: "On March 2, 1955, fifteen-year-old Claudette Colvin refused to surrender her bus seat to a white passenger in Montgomery, Alabama. Police arrested her. This happened nine months before Rosa Parks made a similar refusal. Colvin later became one of four plaintiffs in Browder v. Gayle, the federal case that struck down segregation on Montgomery buses.",
        teachingLayer: {
          visualSummary: [
            { text: "Problem: Jim Crow laws enforced racial separation and denied Black citizens equal treatment." },
            { text: "Action: Claudette refused to cooperate with an unjust rule and later gave testimony in federal court." },
            { text: "Impact: Browder v. Gayle ended legal segregation on Montgomery's public buses in 1956." },
          ],
          deepExplanation: { text: "Movement leaders did not make Colvin the public face of the bus boycott. They believed an adult with Rosa Parks's reputation would be harder for segregationists to attack. That strategy helped the campaign, but it also meant Colvin's role was minimized for decades. History is shaped both by what happened and by which stories institutions choose to repeat." },
          whyItMatters: { text: "Colvin shows that a young person can be central to legal change even when the simplified version of history leaves her out." },
          activity: { text: "Compare two kinds of power: Colvin's personal refusal and her later courtroom testimony. Which challenged the system directly, and which helped change the law?" },
        },
      },
      {
        sceneTitle: { text: "Ruby Bridges: six years old at the schoolhouse door" },
        narration: "On November 14, 1960, six-year-old Ruby Bridges entered William Frantz Elementary School in New Orleans. A federal court had ordered the school to integrate. Federal marshals escorted Ruby past an angry crowd. Many white parents removed their children, and for a time teacher Barbara Henry taught Ruby alone in a classroom.",
        teachingLayer: {
          visualSummary: [
            { text: "Problem: schools remained segregated even after the Supreme Court ruled school segregation unconstitutional in Brown v. Board of Education." },
            { text: "Action: Ruby and her family followed the court order despite threats, isolation, and public hostility." },
            { text: "Impact: her attendance became a visible step in enforcing school integration in the South." },
          ],
          deepExplanation: { text: "Ruby did not create the court case or command the marshals, but the law meant little until a real child walked through the door. Legal victories and lived reality are different stages of change. Enforcement, personal courage, and supportive adults were all necessary." },
          activity: { text: "Make a cause-and-effect chain using these pieces: Brown decision → federal court order → marshals → Ruby enters → school integration becomes real. Add one obstacle at each step." },
        },
      },
      {
        sceneTitle: { text: "Samantha Smith: a letter across the Cold War" },
        narration: "In 1982, ten-year-old Samantha Smith of Maine wrote to Soviet leader Yuri Andropov. The United States and Soviet Union possessed nuclear weapons, and many families feared nuclear war. Samantha asked why the Soviet Union wanted to conquer the world—or whether that accusation was false—and asked what Andropov would do to prevent war. He replied and invited her to visit the Soviet Union in 1983.",
        teachingLayer: {
          visualSummary: [
            { text: "Problem: Cold War propaganda and fear made people on each side imagine the other only as an enemy." },
            { text: "Action: Samantha asked a direct, human question instead of accepting frightening claims without examination." },
            { text: "Impact: her visit received international attention and made ordinary Soviet and American families more visible to one another." },
          ],
          deepExplanation: { text: "Samantha did not end the Cold War, and governments also used public relations for their own purposes. Her importance was different: she demonstrated citizen diplomacy—the power of ordinary people to create contact when leaders speak mainly through threats." },
          activity: { text: "Write one serious question you would ask a powerful leader today. Make it specific enough that a vague slogan would not answer it." },
        },
      },
      {
        sceneTitle: { text: "Malala Yousafzai: insisting that girls belong in school" },
        narration: "Malala Yousafzai grew up in Pakistan's Swat Valley. When the Pakistani Taliban restricted girls' education, she spoke publicly and, at age eleven, wrote an anonymous BBC Urdu diary about life under their rule. In 2012, when she was fifteen, a gunman shot her on a school bus. She survived and continued advocating for education. In 2014, at seventeen, she became the youngest Nobel Peace Prize laureate.",
        teachingLayer: {
          visualSummary: [
            { text: "Problem: armed extremists tried to remove girls from public education through rules, threats, and violence." },
            { text: "Action: Malala documented what was happening and continued speaking after an attempt to silence her." },
            { text: "Impact: her story strengthened international attention and funding for girls' education, including through the Malala Fund." },
          ],
          deepExplanation: { text: "Malala's fame did not single-handedly solve unequal access to education. Millions of local students, parents, and teachers do less visible work. A responsible history lesson honors the symbol while remembering the wider movement." },
          activity: { text: "Explain the difference between awareness and structural change. What can a famous speech accomplish, and what still requires schools, safety, money, laws, and local leadership?" },
        },
      },
      {
        sceneTitle: { text: "The pattern: courage becomes change through a pathway" },
        narration: "These children did different things in different centuries, but their stories share a pattern. Each encountered a barrier. Each chose an action available to them. Other people or institutions carried that action farther. The result became a tool, legal ruling, integrated school, human connection, or worldwide movement.",
        teachingLayer: {
          visualSummary: [
            { text: "Louis Braille: exclusion → invention → literacy system." },
            { text: "Claudette Colvin: segregation → refusal and testimony → court victory." },
            { text: "Ruby Bridges: ignored ruling → brave attendance → enforced integration." },
            { text: "Samantha Smith: nuclear fear → honest letter → citizen diplomacy." },
            { text: "Malala Yousafzai: denied education → testimony and advocacy → global movement." },
          ],
          whyItMatters: { text: "The lesson is not that every child must become famous. It is that noticing clearly, acting faithfully, and joining with others can move something that looked immovable." },
          activity: { text: "Choose two of the five. Create a side-by-side sketchnote showing barrier, action, allies, risk, and lasting change. Finish with one paragraph: Which part of change depends on individual courage, and which part depends on community or law?" },
        },
      },
    ],
  };
}

export default function MissionPage({ params }: { params: Promise<{ missionId: string }> }) {
  const [missionId, setMissionId] = useState("");
  const [query, setQuery] = useState({ type: "lesson", title: "Mission", description: "", track: "TRUTH_HISTORY" });
  const [player, setPlayer] = useState<PlayerProfile | null>(null);
  const [project, setProject] = useState<Item | null>(null);
  const [lesson, setLesson] = useState<AnimatedLesson | null>(null);
  const [sceneIndex, setSceneIndex] = useState(0);
  const [loading, setLoading] = useState(false);
  const [started, setStarted] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [error, setError] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [streamStatus, setStreamStatus] = useState("");
  const [canonicalNote, setCanonicalNote] = useState("");

  async function openCanonicalLesson(missionQuery: MissionQuery, activeSession: PlayerSession, activePlayer: PlayerProfile) {
    if (loading) return;
    setLoading(true); setStreaming(true); setStarted(true); setError(""); setStreamStatus("Checking the curriculum library…"); setCanonicalNote(""); setSceneIndex(0);
    setLesson({ title: { text: missionQuery.title }, learningGoals: [], scenes: [] });
    let receivedBlocks = 0;
    const isChildrenLesson = /children|kids|young people/i.test(missionQuery.title) && /changed|change|history/i.test(missionQuery.title);
    try {
      const response = await fetch("/api/brain/lesson/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${activeSession.token}` },
        body: JSON.stringify({
          student_id: activeSession.studentId,
          track: missionQuery.track,
          topic: missionQuery.title,
          grade_level: activePlayer.grade_level ? String(activePlayer.grade_level) : "8",
          is_homestead: false,
          render_mode: "sketchnote",
          force_regenerate: false,
        }),
      });
      if (!response.ok || !response.body) throw new Error("Adeline could not open the curriculum lesson.");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { value, done } = await reader.read();
        buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });
        const events = buffer.split(/\r?\n\r?\n/);
        buffer = events.pop() ?? "";
        for (const event of events) {
          const dataLine = event.split(/\r?\n/).find((line) => line.startsWith("data:"));
          if (!dataLine) continue;
          const payload = JSON.parse(dataLine.slice(5).trim()) as Item;
          if (payload.type === "status") setStreamStatus(asText(payload.message, "Preparing the next lesson part…"));
          if (payload.type === "error") throw new Error(asText(payload.message, "Adeline could not open this curriculum lesson."));
          if (payload.type === "block" && payload.block && typeof payload.block === "object") {
            const block = payload.block as Item;
            const content = asText(block.content);
            if (asText(block.block_type) === "RESEARCH_MISSION") {
              setStreamStatus("Adeline is handling the research behind the lesson…");
              continue;
            }
            if (/being carefully prepared by our teaching team|status:\s*awaiting review/i.test(content)) {
              throw new Error("This lesson is still under review and does not contain the teaching yet.");
            }
            const scene = blockToScene(block, receivedBlocks);
            receivedBlocks += 1;
            setLesson((current) => ({ ...(current ?? {}), scenes: [...(current?.scenes ?? []), scene] }));
            setLoading(false);
            setStreamStatus("Adding the next part…");
          }
          if (payload.type === "done") {
            const fromCanonical = payload.from_canonical === true;
            setCanonicalNote(fromCanonical ? "✓ Verified canonical lesson · adapted for this learner" : "✓ New master lesson prepared for the canonical curriculum");
            setLesson((current) => ({ ...(current ?? {}), title: { text: asText(payload.title, missionQuery.title) } }));
          }
        }
        if (done) break;
      }
      if (receivedBlocks === 0) throw new Error("This curriculum lesson opened without teaching blocks.");
    } catch (cause) {
      if (isChildrenLesson) {
        setLesson(childrenWhoChangedHistory());
        setCanonicalNote("Saved teaching copy · canonical service temporarily unavailable");
      } else {
        setLesson(null);
        setError(cause instanceof Error ? cause.message : "Adeline could not open this curriculum lesson.");
      }
    } finally {
      setLoading(false); setStreaming(false); setStreamStatus("");
    }
  }

  useEffect(() => {
    const session = getPlayerSession();
    if (!session) { window.location.assign("/sign-in"); return; }
    queueMicrotask(() => setPlayer(session.player));
    const search = new URLSearchParams(window.location.search);
    const nextQuery = { type: search.get("type") === "project" ? "project" : "lesson", title: search.get("title") || "Mission", description: search.get("description") || "", track: search.get("track") || "TRUTH_HISTORY" };
    queueMicrotask(() => setQuery(nextQuery));
    params.then(({ missionId: value }) => {
      const id = decodeURIComponent(value); setMissionId(id);
      if (nextQuery.type === "project") {
        setLoading(true);
        fetch(`/api/brain/projects/${encodeURIComponent(id)}`, { headers: { Authorization: `Bearer ${session.token}` }, cache: "no-store" })
          .then(async (response) => { if (!response.ok) throw new Error("Adeline could not open this project yet."); return response.json(); })
          .then((payload) => setProject(payload as Item)).catch((cause) => setError(cause instanceof Error ? cause.message : "Adeline could not open this project yet."))
          .finally(() => setLoading(false));
      } else {
        void openCanonicalLesson(nextQuery, session, session.player);
      }
    });
  }, [params]);

  const session = useMemo(() => typeof window === "undefined" ? null : getPlayerSession(), [player]);
  const initials = player?.display_name ? player.display_name.split(/\s+/).map((part) => part[0]).join("").slice(0, 2).toUpperCase() : "DA";

  async function beginLesson() {
    if (!session || !player || loading) return;
    await openCanonicalLesson(query, session, player);
  }

  async function beginProject() {
    if (!session || loading) return; setLoading(true); setError("");
    try {
      const response = await fetch(`/api/brain/projects/${encodeURIComponent(missionId)}/start`, { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${session.token}` }, body: JSON.stringify({ student_id: session.studentId, project_id: missionId }) });
      if (!response.ok) throw new Error("This project could not be started yet."); setStarted(true);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "This project could not be started yet."); } finally { setLoading(false); }
  }

  async function finishMission() {
    if (!session || loading) return; setLoading(true); setError("");
    try {
      const isProject = query.type === "project";
      const url = isProject ? `/api/brain/projects/${encodeURIComponent(missionId)}/seal` : "/api/brain/journal/seal";
      const body = isProject ? { student_id: session.studentId, project_id: missionId, reflection: "Completed through My Missions" } : { lesson_id: missionId, track: query.track, completed_blocks: lesson?.scenes?.length ?? 1, oas_standards: [], evidence_sources: [] };
      const response = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${session.token}` }, body: JSON.stringify(body) });
      if (!response.ok) throw new Error("Your work is safe, but the completion record did not save yet."); setCompleted(true);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "The completion record did not save yet."); } finally { setLoading(false); }
  }

  return <main className="dashboard-page"><header className="dashboard-header"><Link href="/">Dear Adeline</Link><span>Mission</span><button type="button" aria-label="Learner profile">{initials}</button></header><div className="dashboard-layout"><DashboardNav active="missions" /><section className="mission-page">
    <Link className="mission-back" href="/dashboard/missions">← My Missions</Link><header className="mission-brief"><p>{query.type === "project" ? "PROJECT MISSION" : "LEARNING MISSION"} · {query.track.replaceAll("_", " ")}</p><h1>{asText(project?.title, query.title)}</h1><span>{asText(project?.tagline, query.description)}</span></header>
    {error && <div className="record-state error">{error}<button type="button" onClick={() => query.type === "project" ? beginProject() : beginLesson()}>Try again</button></div>}
    {loading && <div className="mission-loading"><b>✦</b><h2>{query.type === "project" ? "Opening your workshop…" : "Opening your lesson…"}</h2><p>{query.type === "project" ? "Adeline is gathering the complete project." : streamStatus || "Checking the verified curriculum and adapting it for this learner…"}</p></div>}
    {!loading && query.type === "project" && project && <ProjectMission project={project} started={started} completed={completed} onStart={beginProject} onFinish={finishMission} />}
    {!loading && lesson && <LessonMission lesson={lesson} sceneIndex={sceneIndex} setSceneIndex={setSceneIndex} completed={completed} onFinish={finishMission} streaming={streaming} streamStatus={streamStatus} canonicalNote={canonicalNote} />}
  </section></div></main>;
}

function ProjectMission({ project, started, completed, onStart, onFinish }: { project: Item; started: boolean; completed: boolean; onStart: () => void; onFinish: () => void }) {
  const steps = asList(project.steps) as Item[], materials = asList(project.materials), prompts = asList(project.portfolio_prompts), safety = asList(project.safety_notes);
  return <div className="mission-body"><div className="mission-actions">{!started ? <button onClick={onStart}>Begin this project →</button> : <span>✓ Project underway</span>}<small>{asText(project.estimated_hours)} hours · Grades {asText(project.grade_band)}</small></div>
    <section className="mission-panel"><h2>Gather first</h2><ul>{materials.map((item, index) => <li key={index}>{asText(item)}</li>)}</ul></section>
    {safety.length > 0 && <section className="mission-panel safety"><h2>Safety before speed</h2><ul>{safety.map((item, index) => <li key={index}>{asText(item)}</li>)}</ul></section>}
    <section className="mission-steps"><h2>Build it</h2>{steps.map((step, index) => <article key={index}><b>{asText(step.step_number, String(index + 1))}</b><div><p>{asText(step.instruction)}</p>{step.tip ? <small>Field note: {asText(step.tip)}</small> : null}</div></article>)}</section>
    {prompts.length > 0 && <section className="mission-panel portfolio-prompts"><h2>Proof for your portfolio</h2><ol>{prompts.map((item, index) => <li key={index}>{asText(item)}</li>)}</ol></section>}
    <div className="mission-finish">{completed ? <strong>✓ Mission sealed in your portfolio and transcript.</strong> : <button type="button" disabled={!started} onClick={onFinish}>I finished this mission — save my work</button>}</div></div>;
}

function LessonMission({ lesson, sceneIndex, setSceneIndex, completed, onFinish, streaming, streamStatus, canonicalNote }: { lesson: AnimatedLesson; sceneIndex: number; setSceneIndex: (index: number) => void; completed: boolean; onFinish: () => void; streaming: boolean; streamStatus: string; canonicalNote: string }) {
  const scenes = lesson.scenes ?? [], scene = scenes[sceneIndex]; if (!scene) return <div className="record-state error">This mission opened without any scenes.</div>;
  const layer = scene.teachingLayer ?? {}, points = asList(layer.visualSummary) as Item[];
  const isLastScene = sceneIndex === scenes.length - 1;
  const stage = scene.blockType === "PRIMARY_SOURCE" ? "Examine the evidence" : scene.blockType === "EXPERIMENT" || scene.blockType === "LAB_MISSION" ? "Try it in the real world" : sceneIndex === 0 ? "Come notice this" : isLastScene ? "Make meaning" : "Learn from the story";
  return <div className="lesson-mission">{(streaming || canonicalNote) && <div className="canonical-note">{streaming ? `✦ ${streamStatus || "Adding the next lesson part…"}` : canonicalNote}</div>}<div className="mentor-note"><b>Adeline’s invitation</b><span>{sceneIndex === 0 ? "Come look at this with me. You don’t need to know the answer yet—notice what catches your attention." : "Keep following what makes you curious. I’ll supply the knowledge and context as we go."}</span></div>{(lesson.learningGoals ?? []).length > 0 && <div className="lesson-goals"><span>What this experience will help you understand</span><ul>{(lesson.learningGoals ?? []).map((goal, index) => <li key={index}>{goal}</li>)}</ul></div>}
    <article className="lesson-scene"><header><span>{stage} · Part {sceneIndex + 1} of {scenes.length}</span><h2>{asText(scene.sceneTitle?.text, asText(lesson.title?.text, "Mission scene"))}</h2></header><p className="scene-narration">{scene.narration}</p>{points.length > 0 && <ul className="scene-points">{points.map((point, index) => <li key={index}>{asText(point.text)}</li>)}</ul>}{layer.deepExplanation ? <div className="scene-deep"><b>Here’s what experience teaches us</b><p>{asText((layer.deepExplanation as Item).text)}</p></div> : null}{layer.whyItMatters ? <div className="scene-matters"><b>Why this matters beyond school</b><p>{asText((layer.whyItMatters as Item).text)}</p></div> : null}{layer.activity ? <div className="scene-activity"><b>Try it now that you know enough</b><p>{asText((layer.activity as Item).text)}</p></div> : null}</article>
    {isLastScene && <LessonExtras lesson={lesson} />}
    <div className="scene-controls"><button disabled={sceneIndex === 0} onClick={() => setSceneIndex(sceneIndex - 1)}>← Back</button><div>{scenes.map((_, index) => <button aria-label={`Scene ${index + 1}`} className={index === sceneIndex ? "active" : ""} key={index} onClick={() => setSceneIndex(index)} />)}</div>{!isLastScene ? <button onClick={() => setSceneIndex(sceneIndex + 1)}>Next →</button> : completed ? <strong>✓ Mission saved</strong> : <button onClick={onFinish}>Finish & save →</button>}</div></div>;
}

function LessonExtras({ lesson }: { lesson: AnimatedLesson }) {
  const vocabulary = lesson.vocabulary ?? [], assessment = lesson.assessment ?? [], extensions = lesson.extensionActivities ?? [];
  if (!vocabulary.length && !assessment.length && !extensions.length) return null;
  return <section className="lesson-extras">
    {vocabulary.length > 0 && <div><h2>Words worth keeping</h2><dl>{vocabulary.map((item, index) => <div key={index}><dt>{asText(item.word)}</dt><dd>{asText(item.definition)}{item.pronunciation ? <small>Say it: {asText(item.pronunciation)}</small> : null}</dd></div>)}</dl></div>}
    {assessment.length > 0 && <div><h2>Check your understanding</h2><ol>{assessment.map((item, index) => <li key={index}><p>{asText(item.question)}</p>{item.answer ? <details><summary>Check the answer</summary><span>{asText(item.answer)}</span></details> : null}</li>)}</ol></div>}
    {extensions.length > 0 && <div><h2>Take it into the real world</h2>{extensions.map((item, index) => <article key={index}><h3>{asText(item.title, `Extension ${index + 1}`)}</h3><p>{asText(item.instructions)}</p>{asList(item.materials).length > 0 && <small>Materials: {asList(item.materials).map((material) => asText(material)).join(", ")}</small>}</article>)}</div>}
  </section>;
}
