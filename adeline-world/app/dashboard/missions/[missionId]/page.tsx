"use client";

import { useEffect, useMemo, useState } from "react";
import DashboardNav from "../../DashboardNav";
import { getPlayerSession, PlayerProfile } from "../../../lib/player-session";

type Item = Record<string, unknown>;
type Scene = { sceneTitle?: { text?: string }; narration?: string; teachingLayer?: Item };
type AnimatedLesson = {
  title?: { text?: string };
  learningGoals?: string[];
  scenes?: Scene[];
  vocabulary?: Item[];
  assessment?: Item[];
  extensionActivities?: Item[];
};
type MissionQuery = { type: string; title: string; description: string; track: string };
function asText(value: unknown, fallback = "") { return typeof value === "string" || typeof value === "number" ? String(value) : fallback; }
function asList(value: unknown) { return Array.isArray(value) ? value : []; }

function adelineFocus(query: MissionQuery) {
  return [
    query.description,
    "Teach the subject itself thoroughly before asking the learner to research, write, build, or respond.",
    "Use Adeline's real voice: warm, sharp-witted, conversational, and never formulaic or childish.",
    "Ground factual claims in specific evidence. Name the real people, dates, documents, laws, experiments, measurements, institutions, and incentives involved.",
    "For history and justice: do not sanitize. Show how events unfolded, who held power, who profited, who suffered, what the original records show, and how people created change.",
    "Distinguish verified evidence from interpretation. Cite primary sources inline whenever possible and say plainly when the record is uncertain.",
    "Work comes after instruction. Activities must have purpose: help someone, solve a real problem, reveal understanding, or create a portfolio-worthy accomplishment. No busywork.",
    "Maintain a Biblical worldview naturally: every person has inherent worth, knowledge without love is empty, power needs accountability, and truth does not fear examination.",
  ].filter(Boolean).join("\n");
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

function readyMission(query: MissionQuery): AnimatedLesson {
  const topic = query.title || "Your mission";
  if (/children|kids|young people/i.test(topic) && /changed|change|history/i.test(topic)) {
    return childrenWhoChangedHistory();
  }
  const focus = query.description || `Investigate ${topic}, explain what you discover, and create evidence of your learning.`;
  return {
    title: { text: topic },
    learningGoals: [
      `Explain the central ideas behind ${topic}.`,
      "Separate strong evidence from assumptions or unsupported claims.",
      "Create something that demonstrates what you learned.",
    ],
    scenes: [
      { sceneTitle: { text: "Start with what you notice" }, narration: focus, teachingLayer: { visualSummary: [{ text: `Write three things you already think you know about ${topic}.` }, { text: "Circle the one idea you most need to verify." }], whyItMatters: { text: "Naming your starting beliefs makes it easier to notice when evidence changes your mind." }, activity: { text: "Make a quick sketchnote: What I know, What I suspect, and What I need to find out." } } },
      { sceneTitle: { text: "Investigate the evidence" }, narration: `Now dig beneath the surface of ${topic}. Look for causes, effects, people affected, and the evidence behind each claim.`, teachingLayer: { visualSummary: [{ text: "Find at least two useful sources or real-world examples." }, { text: "Record the source beside every important fact." }, { text: "Notice who benefits, who carries the cost, and what may be missing." }], deepExplanation: { text: "Strong investigation compares evidence instead of accepting the first confident answer. Primary sources, direct observations, original data, and real results deserve special attention." }, activity: { text: "Build an evidence map with four branches: facts, causes, effects, and unanswered questions." } } },
      { sceneTitle: { text: "Make meaning" }, narration: `Use the evidence to explain ${topic} in your own words—not copied language.`, teachingLayer: { visualSummary: [{ text: "State your main conclusion in one clear sentence." }, { text: "Support it with the strongest evidence you found." }, { text: "Name one limit, disagreement, or question that remains." }], whyItMatters: { text: "Real learning means you can explain an idea, defend it with evidence, and stay honest about what you do not yet know." }, activity: { text: "Teach the idea aloud to someone, or record a two-minute explanation. Revise any part that is hard to explain." } } },
      { sceneTitle: { text: "Create your proof" }, narration: "Turn your learning into something worth keeping in your portfolio.", teachingLayer: { visualSummary: [{ text: "Choose a product: illustrated page, model, experiment, letter, video, presentation, or another fitting creation." }, { text: "Include your conclusion and supporting evidence." }, { text: "Add a short reflection about what changed in your thinking." }], activity: { text: `Create and finish your evidence piece for ${topic}. Photograph, upload, or save the finished work before sealing the mission.` } } },
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
      } else {
        setLoading(true); setStarted(true);
        fetch("/api/brain/brain/lesson/animated", { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${session.token}` }, body: JSON.stringify({ topic: nextQuery.title, focus: adelineFocus(nextQuery), duration_seconds: 600, target_ages: session.player.grade_level ? `grade ${session.player.grade_level}` : "10-18", track: nextQuery.track, student_id: session.studentId }) })
          .then(async (response) => response.ok ? response.json() as Promise<AnimatedLesson> : readyMission(nextQuery))
          .then((payload) => setLesson(payload))
          .catch(() => setLesson(readyMission(nextQuery)))
          .finally(() => setLoading(false));
      }
    });
  }, [params]);

  const session = useMemo(() => typeof window === "undefined" ? null : getPlayerSession(), [player]);
  const initials = player?.display_name ? player.display_name.split(/\s+/).map((part) => part[0]).join("").slice(0, 2).toUpperCase() : "DA";

  async function beginLesson() {
    if (!session || loading) return; setLoading(true); setError(""); setStarted(true);
    try {
      const response = await fetch("/api/brain/brain/lesson/animated", { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${session.token}` }, body: JSON.stringify({ topic: query.title, focus: adelineFocus(query), duration_seconds: 600, target_ages: player?.grade_level ? `grade ${player.grade_level}` : "10-18", track: query.track, student_id: session.studentId }) });
      setLesson(response.ok ? await response.json() as AnimatedLesson : readyMission(query));
    } catch { setLesson(readyMission(query)); } finally { setLoading(false); }
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
  const isLastScene = sceneIndex === scenes.length - 1;
  return <div className="lesson-mission"><div className="lesson-goals"><span>Mission goals</span><ul>{(lesson.learningGoals ?? []).map((goal, index) => <li key={index}>{goal}</li>)}</ul></div>
    <article className="lesson-scene"><header><span>Scene {sceneIndex + 1} of {scenes.length}</span><h2>{asText(scene.sceneTitle?.text, asText(lesson.title?.text, "Mission scene"))}</h2></header><p className="scene-narration">{scene.narration}</p>{points.length > 0 && <ul className="scene-points">{points.map((point, index) => <li key={index}>{asText(point.text)}</li>)}</ul>}{layer.deepExplanation ? <div className="scene-deep"><b>Look closer</b><p>{asText((layer.deepExplanation as Item).text)}</p></div> : null}{layer.whyItMatters ? <div className="scene-matters"><b>Why it matters</b><p>{asText((layer.whyItMatters as Item).text)}</p></div> : null}{layer.activity ? <div className="scene-activity"><b>Your move</b><p>{asText((layer.activity as Item).text)}</p></div> : null}</article>
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
