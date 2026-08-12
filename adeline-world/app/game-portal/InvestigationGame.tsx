"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { getPlayerSession } from "../lib/player-session";
import PhaserCaseMap from "./PhaserCaseMap";

type Stop = { id: string; name: string; icon: string; guide: string; scene: string; record: string; source: string; context: string };

const stops: Stop[] = [
  { id: "bus", name: "Cleveland Avenue Bus", icon: "🚌", guide: "Passenger", scene: "Montgomery, March 2, 1955. Claudette Colvin, age fifteen, is riding home from school. The driver orders her row to give up its seats. She refuses and is arrested.", record: "Colvin later described knowing about the Constitution and believing she had a right to remain seated.", source: "Oral history", context: "A participant’s memory explains motive and experience. It is valuable, but it was recorded years after the event." },
  { id: "newsroom", name: "Newsroom", icon: "📰", guide: "Editor", scene: "A newspaper can tell you what the public was told—and what editors thought readers would accept. Its silence can matter too.", record: "Contemporary coverage records Colvin’s arrest, but later public memory centered more heavily on Rosa Parks and the boycott.", source: "Contemporary reporting", context: "Created near the event, yet shaped by an editor, audience, vocabulary, and the racial order of the time." },
  { id: "organizer", name: "Organizer’s Kitchen", icon: "☕", guide: "Community organizer", scene: "Leaders needed a case that could survive hostile courts and unite a frightened community. They judged not only the injustice, but the risks around the person carrying it.", record: "Colvin’s age and later pregnancy affected leaders’ strategy. That does not make her action less courageous; it reveals the pressures movements face.", source: "Movement history", context: "Strategy explains why a movement may elevate one story and protect or sideline another." },
  { id: "courthouse", name: "Federal Courthouse", icon: "🏛️", guide: "Court clerk", scene: "A protest can expose an injustice. A lawsuit can force the government to answer it. Colvin and three other women became plaintiffs in Browder v. Gayle.", record: "The federal case held bus segregation unconstitutional. The Supreme Court affirmed the ruling in 1956, ending Montgomery’s bus-segregation law.", source: "Court record", context: "A legal record is strong for what a court decided, but it rarely contains the whole human story behind the case." },
];

const conclusions = [
  { id: "single", text: "One famous person ended bus segregation by acting alone." },
  { id: "network", text: "Young courage, organized community action, and a constitutional court case worked together—and public memory left some people out." },
  { id: "court", text: "The judges created the movement; the people involved were mostly unimportant." },
];

export default function InvestigationGame({ onClose }: { onClose: () => void }) {
  const [location, setLocation] = useState(stops[0].id);
  const [found, setFound] = useState<string[]>([]);
  const [view, setView] = useState<"map" | "case">("map");
  const [choice, setChoice] = useState("");
  const [result, setResult] = useState<"ready" | "revise" | "solved">("ready");
  const [reflection, setReflection] = useState("");
  const [minutes, setMinutes] = useState("45");
  const [saveState, setSaveState] = useState<"ready" | "saving" | "saved" | "error">("ready");
  const [saveMessage, setSaveMessage] = useState("");
  const [photo, setPhoto] = useState<File | null>(null);
  const [photoState, setPhotoState] = useState<"ready" | "saving" | "saved" | "error">("ready");
  const current = stops.find((stop) => stop.id === location) || stops[0];
  const discovered = useMemo(() => stops.filter((stop) => found.includes(stop.id)), [found]);
  const addRecord = () => setFound((items) => items.includes(current.id) ? items : [...items, current.id]);
  const solve = () => { if (found.length === stops.length) setResult(choice === "network" ? "solved" : "revise"); };

  useEffect(() => {
    const session = getPlayerSession();
    if (session && localStorage.getItem(`adeline_case_colvin_${session.studentId}`) === "saved") {
      setFound(stops.map((stop) => stop.id)); setChoice("network"); setResult("solved"); setSaveState("saved");
      setSaveMessage("This case is already part of your learning record.");
    }
  }, []);

  async function saveCase(event: FormEvent) {
    event.preventDefault();
    const session = getPlayerSession();
    if (!session || saveState === "saving") { setSaveState("error"); setSaveMessage("Sign in as a learner so Adeline can save this work."); return; }
    setSaveState("saving"); setSaveMessage("");
    try {
      const headers = { "Content-Type": "application/json", Authorization: `Bearer ${session.token}` };
      const journal = await fetch("/api/brain/journal/seal", { method: "POST", headers, body: JSON.stringify({ lesson_id: "game-teenager-history-nearly-forgot", track: "JUSTICE_CHANGEMAKING", completed_blocks: 4, oas_standards: [], evidence_sources: stops.map((stop) => stop.source) }) });
      if (!journal.ok) throw new Error("The case is complete, but Adeline could not save the learning record yet.");
      const activity = await fetch("/api/brain/brain/activities/report", { method: "POST", headers, body: JSON.stringify({ student_id: session.studentId, grade_level: String(session.player.grade_level || 8), description: `Historical investigation: The Teenager History Nearly Forgot. Learner conclusion: ${reflection.trim()}`, time_minutes: Math.max(10, Math.min(240, Number(minutes) || 45)) }) });
      if (!activity.ok) throw new Error("The case was journaled, but the portfolio and credit record did not finish.");
      localStorage.setItem(`adeline_case_colvin_${session.studentId}`, "saved");
      setSaveState("saved"); setSaveMessage("Saved to your journal, portfolio, and credit record.");
    } catch (cause) { setSaveState("error"); setSaveMessage(cause instanceof Error ? cause.message : "Adeline could not save this case yet."); }
  }

  async function addPhoto(event: FormEvent) {
    event.preventDefault(); const session = getPlayerSession();
    if (!session || !photo || photoState === "saving") return;
    setPhotoState("saving");
    try {
      const auth = { Authorization: `Bearer ${session.token}` };
      const match = await fetch("/api/brain/brain/api/standards/match", { method: "POST", headers: { ...auth, "Content-Type": "application/json" }, body: JSON.stringify({ content: "Compare historical sources and explain how Claudette Colvin, community organizers, and Browder v. Gayle changed bus segregation", track: "JUSTICE_CHANGEMAKING", grade: Number(session.player.grade_level) || 8, top_k: 1 }) });
      if (!match.ok) throw new Error(); const data = await match.json() as { standards?: { code?: string }[] }; const standard = data.standards?.[0]?.code; if (!standard) throw new Error();
      const form = new FormData(); form.set("student_id", session.studentId); form.set("standard_id", standard); form.set("evidence_type", "photo"); form.set("description", "Portfolio creation from The Teenager History Nearly Forgot investigation"); form.set("file", photo);
      const upload = await fetch("/api/brain/brain/api/standards/evidence/upload", { method: "POST", headers: auth, body: form }); if (!upload.ok) throw new Error();
      setPhotoState("saved"); setPhoto(null);
    } catch { setPhotoState("error"); }
  }

  return <section className="investigation-game" aria-label="The teenager history nearly forgot investigation game">
    <header><button type="button" onClick={onClose}>← Town map</button><div><span>HISTORY INVESTIGATION · CASE 01</span><h1>The Teenager History Nearly Forgot</h1></div><strong>{found.length}/{stops.length} records</strong></header>
    <nav className="case-tabs" aria-label="Investigation views"><button className={view === "map" ? "active" : ""} onClick={() => setView("map")}>Explore Montgomery</button><button className={view === "case" ? "active" : ""} onClick={() => setView("case")}>Case board {found.length ? `(${found.length})` : ""}</button></nav>
    {view === "map" ? <div className="investigation-layout">
      <aside className="case-brief"><span>THE QUESTION</span><h2>How does change actually happen—and whose courage gets remembered?</h2><p>Visit each place. Listen, inspect its record, and notice what that kind of source can and cannot tell you.</p><div className="case-progress">{stops.map((stop) => <i className={found.includes(stop.id) ? "found" : ""} key={stop.id}>{found.includes(stop.id) ? "✓" : "·"} {stop.name}</i>)}</div></aside>
      <PhaserCaseMap visited={found} onVisit={(id) => setLocation(id)} />
      <article className="source-scene"><span>{current.icon} {current.name}</span><h2>{current.guide}</h2><p>{current.scene}</p><blockquote>{current.record}</blockquote><div><b>{current.source}</b><small>{current.context}</small></div><button type="button" onClick={addRecord} disabled={found.includes(current.id)}>{found.includes(current.id) ? "Added to case board ✓" : "Pin this record"}</button></article>
    </div> : <div className="case-board">
      <section><span>YOUR DISCOVERIES</span><h2>Build the fuller account</h2>{!discovered.length && <p>Explore the city and pin records here first.</p>}<div className="clue-grid">{discovered.map((stop) => <article key={stop.id}><b>{stop.icon} {stop.source}</b><p>{stop.record}</p><small>{stop.context}</small></article>)}</div></section>
      <aside className="case-conclusion"><span>MAKE YOUR CALL</span><h2>Which account fits all four places?</h2>{conclusions.map((item) => <label key={item.id}><input type="radio" name="conclusion" checked={choice === item.id} onChange={() => { setChoice(item.id); setResult("ready"); }} /><span>{item.text}</span></label>)}<button onClick={solve} disabled={!choice || found.length < stops.length}>Close the case</button>{found.length < stops.length && <p className="case-feedback">The board still has empty spaces. A strong conclusion has to account for every kind of record.</p>}{result === "revise" && <p className="case-feedback revise">That account ignores part of the record. Revisit the organizer and courthouse cards: individual courage mattered, but change also needed organized people and law.</p>}{result === "solved" && <div className="case-solved"><b>Case solved</b><p>You found the pattern: courage began the story, organization sustained it, and law made the change enforceable. Claudette Colvin belongs in that fuller history.</p>{saveState !== "saved" ? <form onSubmit={saveCase}><label>In your own words, what caused the change?<textarea required minLength={20} value={reflection} onChange={(event) => setReflection(event.target.value)} placeholder="Courage began it, but…" /></label><label>About how many minutes did you investigate?<input type="number" min="10" max="240" required value={minutes} onChange={(event) => setMinutes(event.target.value)} /></label><button disabled={saveState === "saving"}>{saveState === "saving" ? "Saving your work…" : "Save my case →"}</button></form> : <><strong className="case-save-message">✓ {saveMessage}</strong><form className="case-photo" onSubmit={addPhoto}><label>Add a photo of a timeline, drawing, written argument, or family discussion board to your portfolio.<input type="file" accept="image/jpeg,image/png,image/gif" onChange={(event) => setPhoto(event.target.files?.[0] || null)} /></label><button disabled={!photo || photoState === "saving"}>{photoState === "saving" ? "Adding…" : "Add portfolio photo"}</button>{photoState === "saved" && <small>Photo added to your portfolio.</small>}{photoState === "error" && <small>That photo did not save yet. Your completed case is still safe.</small>}</form><div className="next-case"><span>NEXT MISSION</span><b>From Courage to Constitutional Change</b><p>Follow one young person’s action through organizing, court strategy, and lasting law—then find whose work the famous version leaves out.</p><Link href="/dashboard/missions/starter-justice_changemaking-0?type=lesson&title=Children%20Who%20Changed%20History&description=Young%20people%20whose%20courage%20changed%20the%20world&track=JUSTICE_CHANGEMAKING">Open the next mission →</Link></div></>} {saveState === "error" && <small className="case-save-error">{saveMessage}</small>}<button type="button" onClick={onClose}>Return to town</button></div>}</aside>
    </div>}
    <footer>Historical statements are paraphrased for gameplay. The source notes teach how historians weigh different records.</footer>
  </section>;
}
