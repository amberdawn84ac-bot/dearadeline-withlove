"use client";

import { useEffect, useMemo, useState } from "react";
import DashboardNav from "../../DashboardNav";
import { getPlayerSession, PlayerProfile } from "../../../lib/player-session";

type Item = Record<string, unknown>;
type Scene = { sceneTitle?: { text?: string }; narration?: string; teachingLayer?: Item };
type AnimatedLesson = { title?: { text?: string }; learningGoals?: string[]; scenes?: Scene[] };
function asText(value: unknown, fallback = "") { return typeof value === "string" || typeof value === "number" ? String(value) : fallback; }
function asList(value: unknown) { return Array.isArray(value) ? value : []; }

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

  useEffect(() => {
    const session = getPlayerSession();
    if (!session) { window.location.assign("/sign-in"); return; }
    setPlayer(session.player);
    const search = new URLSearchParams(window.location.search);
    const nextQuery = { type: search.get("type") === "project" ? "project" : "lesson", title: search.get("title") || "Mission", description: search.get("description") || "", track: search.get("track") || "TRUTH_HISTORY" };
    setQuery(nextQuery);
    params.then(({ missionId: value }) => {
      const id = decodeURIComponent(value); setMissionId(id);
      if (nextQuery.type === "project") {
        setLoading(true);
        fetch(`/api/brain/projects/${encodeURIComponent(id)}`, { headers: { Authorization: `Bearer ${session.token}` }, cache: "no-store" })
          .then(async (response) => { if (!response.ok) throw new Error("Adeline could not open this project yet."); return response.json(); })
          .then((payload) => setProject(payload as Item)).catch((cause) => setError(cause instanceof Error ? cause.message : "Adeline could not open this project yet."))
          .finally(() => setLoading(false));
      }
    });
  }, [params]);

  const session = useMemo(() => typeof window === "undefined" ? null : getPlayerSession(), [player]);
  const initials = player?.display_name ? player.display_name.split(/\s+/).map((part) => part[0]).join("").slice(0, 2).toUpperCase() : "DA";

  async function beginLesson() {
    if (!session || loading) return; setLoading(true); setError(""); setStarted(true);
    try {
      const response = await fetch("/api/brain/lesson/animated", { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${session.token}` }, body: JSON.stringify({ topic: query.title, focus: query.description, duration_seconds: 600, target_ages: player?.grade_level ? `grade ${player.grade_level}` : "10-18", track: query.track, student_id: session.studentId }) });
      if (!response.ok) throw new Error("Adeline could not build this mission yet. Please try again.");
      setLesson(await response.json() as AnimatedLesson);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Adeline could not build this mission yet."); } finally { setLoading(false); }
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

  return <main className="dashboard-page"><header className="dashboard-header"><a href="/">Dear Adeline</a><span>Mission</span><button type="button" aria-label="Learner profile">{initials}</button></header><div className="dashboard-layout"><DashboardNav active="missions" /><section className="mission-page">
    <a className="mission-back" href="/dashboard/missions">← My Missions</a><header className="mission-brief"><p>{query.type === "project" ? "PROJECT MISSION" : "LEARNING MISSION"} · {query.track.replaceAll("_", " ")}</p><h1>{asText(project?.title, query.title)}</h1><span>{asText(project?.tagline, query.description)}</span></header>
    {error && <div className="record-state error">{error}<button type="button" onClick={() => query.type === "project" ? beginProject() : beginLesson()}>Try again</button></div>}
    {loading && <div className="mission-loading"><b>✦</b><h2>{query.type === "project" ? "Opening your workshop…" : "Adeline is drawing your mission…"}</h2><p>She is shaping it around this learner—not pulling a generic worksheet from a filing cabinet.</p></div>}
    {!loading && query.type === "project" && project && <ProjectMission project={project} started={started} completed={completed} onStart={beginProject} onFinish={finishMission} />}
    {!loading && query.type === "lesson" && !lesson && <div className="mission-launch"><b>✦</b><h2>Ready to enter?</h2><p>This opens as an interactive sketchnote mission built around the topic, the learner’s grade, and the selected track.</p><button type="button" onClick={beginLesson}>Begin mission →</button></div>}
    {!loading && lesson && <LessonMission lesson={lesson} sceneIndex={sceneIndex} setSceneIndex={setSceneIndex} completed={completed} onFinish={finishMission} />}
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

function LessonMission({ lesson, sceneIndex, setSceneIndex, completed, onFinish }: { lesson: AnimatedLesson; sceneIndex: number; setSceneIndex: (index: number) => void; completed: boolean; onFinish: () => void }) {
  const scenes = lesson.scenes ?? [], scene = scenes[sceneIndex]; if (!scene) return <div className="record-state error">This mission opened without any scenes.</div>;
  const layer = scene.teachingLayer ?? {}, points = asList(layer.visualSummary) as Item[];
  return <div className="lesson-mission"><div className="lesson-goals"><span>Mission goals</span><ul>{(lesson.learningGoals ?? []).map((goal, index) => <li key={index}>{goal}</li>)}</ul></div>
    <article className="lesson-scene"><header><span>Scene {sceneIndex + 1} of {scenes.length}</span><h2>{asText(scene.sceneTitle?.text, asText(lesson.title?.text, "Mission scene"))}</h2></header><p className="scene-narration">{scene.narration}</p>{points.length > 0 && <ul className="scene-points">{points.map((point, index) => <li key={index}>{asText(point.text)}</li>)}</ul>}{layer.deepExplanation ? <div className="scene-deep"><b>Look closer</b><p>{asText((layer.deepExplanation as Item).text)}</p></div> : null}{layer.whyItMatters ? <div className="scene-matters"><b>Why it matters</b><p>{asText((layer.whyItMatters as Item).text)}</p></div> : null}{layer.activity ? <div className="scene-activity"><b>Your move</b><p>{asText((layer.activity as Item).text)}</p></div> : null}</article>
    <div className="scene-controls"><button disabled={sceneIndex === 0} onClick={() => setSceneIndex(sceneIndex - 1)}>← Back</button><div>{scenes.map((_, index) => <button aria-label={`Scene ${index + 1}`} className={index === sceneIndex ? "active" : ""} key={index} onClick={() => setSceneIndex(index)} />)}</div>{sceneIndex < scenes.length - 1 ? <button onClick={() => setSceneIndex(sceneIndex + 1)}>Next →</button> : completed ? <strong>✓ Mission saved</strong> : <button onClick={onFinish}>Finish & save →</button>}</div></div>;
}
