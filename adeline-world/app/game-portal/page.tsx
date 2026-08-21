"use client";

import { FormEvent, useEffect, useState } from "react";
import InvestigationGame from "./InvestigationGame";

type Command = "forward" | "left" | "right";
type Robot = { x: number; y: number; direction: number };
type WorldObject = { id: string; x: number; y: number; sprite: string; label: string; effect: string };

const worldLevels: Record<string, { title: string; brief: string; player: string; goal: string; objects: WorldObject[] }> = {
  justice: { title: "The Missing Voices", brief: "Move through the town, recover six firsthand accounts, and bring them to Civic Hall before the official story hardens.", player: "🕵️", goal: "🏛️", objects: ["Letter", "Ledger", "Photo", "Map", "Testimony", "Receipt"].map((label, i) => ({ id: label, x: [2,4,7,9,3,8][i], y: [6,2,6,3,1,1][i], sprite: ["✉️","📒","📷","🗺️","🗣️","🧾"][i], label, effect: `${label} adds a missing piece to the account.` })) },
  greenhouse: { title: "Save the Seedlings", brief: "Gather what the irrigation system needs, avoid the dry beds, and restore water to the greenhouse.", player: "🧑‍🌾", goal: "🌱", objects: ["Pipe", "Valve", "Rain barrel", "Mulch", "Filter", "Drip line"].map((label, i) => ({ id: label, x: [2,4,7,9,3,8][i], y: [6,2,6,3,1,1][i], sprite: ["➖","🔧","🛢️","🍂","⚙️","💧"][i], label, effect: `${label} improves the working irrigation system.` })) },
  market: { title: "Market Day Rescue", brief: "Collect the tools for a fair, sustainable market stall and reach Market Square without wasting the budget.", player: "🧺", goal: "🏪", objects: ["Price tags", "Scale", "Change", "Sign", "Inventory", "Receipt book"].map((label, i) => ({ id: label, x: [2,4,7,9,3,8][i], y: [6,2,6,3,1,1][i], sprite: ["🏷️","⚖️","🪙","🪧","📦","📕"][i], label, effect: `${label} makes the market more useful and accountable.` })) },
  history: { title: "Timewalker", brief: "Recover six pieces of the historical record, then carry the fuller story safely through the history portal.", player: "🧭", goal: "🌀", objects: ["Diary", "Newspaper", "Artifact", "Portrait", "Law", "Oral history"].map((label, i) => ({ id: label, x: [2,4,7,9,3,8][i], y: [6,2,6,3,1,1][i], sprite: ["📔","📰","🏺","🖼️","📜","🎙️"][i], label, effect: `${label} reveals another perspective from the time.` })) },
};

const defaultLevel = { title: "Town Quest", brief: "Explore the district, collect the six tools that matter, and bring them to the destination.", player: "🧑‍🚀", goal: "✨", objects: ["Tool", "Clue", "Plan", "Material", "Record", "Key"].map((label, i) => ({ id: label, x: [2,4,7,9,3,8][i], y: [6,2,6,3,1,1][i], sprite: ["🔧","🔎","📐","🧱","📓","🗝️"][i], label, effect: `${label} helps complete the mission.` })) };
const worldObstacles = new Set(["5,0","5,1","5,2","5,4","5,5","5,6","1,3","2,3","8,4","9,4","10,4"]);

const buildings = [
  {
    id: "computer",
    name: "Codeworks Lab",
    icon: "⌘",
    position: "portal-computer",
    color: "sapphire",
    area: "Computer Science",
    mission: "Build a tiny arcade game and debug three broken commands.",
    reward: "Debugging I · 180 XP",
  },
  {
    id: "justice",
    name: "Justice Center",
    icon: "⚖",
    position: "portal-justice",
    color: "ruby",
    area: "History · Government · English",
    mission: "Investigate a real case, map the evidence, and argue what should change.",
    reward: "Evidence & Argument I · 220 XP",
  },
  {
    id: "greenhouse",
    name: "Greenhouse Grounds",
    icon: "♧",
    position: "portal-greenhouse",
    color: "emerald",
    area: "Biology · Math · Food Systems",
    mission: "Design an irrigation route using ratios, area, and real plant needs.",
    reward: "Applied Measurement I · 200 XP",
  },
  {
    id: "maker",
    name: "Maker Barn",
    icon: "⚒",
    position: "portal-maker",
    color: "gold",
    area: "Engineering · Design",
    mission: "Prototype a useful tool from limited materials and test it under pressure.",
    reward: "Prototype Builder I · 190 XP",
  },
  {
    id: "library",
    name: "Lantern Library",
    icon: "▤",
    position: "portal-library",
    color: "amethyst",
    area: "Literature · Research · Writing",
    mission: "Unlock a mystery by comparing sources and spotting the unreliable narrator.",
    reward: "Source Sleuth I · 210 XP",
  },
  {
    id: "observatory",
    name: "Skyglass Observatory",
    icon: "✦",
    position: "portal-observatory",
    color: "turquoise",
    area: "Physics · Earth & Space",
    mission: "Track a strange signal, graph its wave pattern, and identify its source.",
    reward: "Pattern Finder I · 230 XP",
  },
  {
    id: "civic",
    name: "Civic Hall",
    icon: "⌂",
    position: "portal-civic",
    color: "indigo",
    area: "Government · Leadership · Community",
    mission: "Join the town council, weigh competing needs, and build a budget players can live with.",
    reward: "Community Steward I · 240 XP",
  },
  {
    id: "wellness",
    name: "Wellness House",
    icon: "♡",
    position: "portal-wellness",
    color: "coral",
    area: "Health · Human Biology · Life Skills",
    mission: "Trace a resident’s symptoms, compare evidence, and design a realistic care plan.",
    reward: "Health Investigator I · 190 XP",
  },
  {
    id: "market",
    name: "Market Square",
    icon: "◇",
    position: "portal-market",
    color: "garnet",
    area: "Economics · Business · Math",
    mission: "Open a market stall, price your goods, and adapt when the town economy changes.",
    reward: "Market Maker I · 210 XP",
  },
  {
    id: "history",
    name: "History Portal",
    icon: "⌛",
    position: "portal-history",
    color: "bronze",
    area: "History · Culture · Cause & Effect",
    mission: "Enter a turning point in history, choose a role, and live with the consequences.",
    reward: "Time Witness I · 250 XP",
  },
];

export default function GamePortal() {
  const [selected, setSelected] = useState(buildings[0]);
  const [player, setPlayer] = useState({ x: 42, y: 64 });
  const [labOpen, setLabOpen] = useState(false);
  const [worldOpen, setWorldOpen] = useState(false);
  const [investigationOpen, setInvestigationOpen] = useState(false);
  const [worldPlayer, setWorldPlayer] = useState({ x: 0, y: 7 });
  const [collected, setCollected] = useState<string[]>([]);
  const [worldMessage, setWorldMessage] = useState("Use the arrow keys or controls to explore.");
  const [commands, setCommands] = useState<Command[]>([]);
  const [robot, setRobot] = useState<Robot>({ x: 0, y: 4, direction: 0 });
  const [runState, setRunState] = useState<"ready" | "running" | "success" | "failed">("ready");
  const [makeCodeUrl, setMakeCodeUrl] = useState("");
  const [projectTitle, setProjectTitle] = useState("");
  const [projectExplanation, setProjectExplanation] = useState("");
  const [savedProjects, setSavedProjects] = useState<Array<{ title: string; url: string; explanation: string }>>([]);

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem("adeline-makecode-projects");
      if (saved) setSavedProjects(JSON.parse(saved));
    } catch { /* A project can still be submitted during this visit. */ }
  }, []);

  function saveMakeCodeProject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const url = makeCodeUrl.trim();
    if (!/^https:\/\/arcade\.makecode\.com\/(?:S|_)[A-Za-z0-9_-]+/i.test(url)) return;
    const next = [{ title: projectTitle.trim() || "My Arcade Game", url, explanation: projectExplanation.trim() }, ...savedProjects];
    setSavedProjects(next);
    window.localStorage.setItem("adeline-makecode-projects", JSON.stringify(next));
    setMakeCodeUrl("");
    setProjectTitle("");
    setProjectExplanation("");
  }

  function movePlayer(dx: number, dy: number) {
    setPlayer((current) => ({
      x: Math.max(5, Math.min(90, current.x + dx)),
      y: Math.max(8, Math.min(78, current.y + dy)),
    }));
  }

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (labOpen || worldOpen || investigationOpen) return;
      const moves: Record<string, [number, number]> = {
        ArrowUp: [0, -2.5], ArrowDown: [0, 2.5], ArrowLeft: [-2.5, 0], ArrowRight: [2.5, 0],
      };
      const move = moves[event.key];
      if (!move) return;
      event.preventDefault();
      movePlayer(...move);
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [labOpen, worldOpen, investigationOpen]);

  const level = worldLevels[selected.id] || defaultLevel;

  function openWorld() {
    setWorldPlayer({ x: 0, y: 7 });
    setCollected([]);
    setWorldMessage("Find the six useful objects, then reach the glowing destination.");
    setWorldOpen(true);
  }

  function moveInWorld(dx: number, dy: number) {
    setWorldPlayer((current) => {
      const next = { x: Math.max(0, Math.min(11, current.x + dx)), y: Math.max(0, Math.min(7, current.y + dy)) };
      if (worldObstacles.has(`${next.x},${next.y}`)) {
        setWorldMessage("That route is blocked. Find another way through.");
        return current;
      }
      const found = level.objects.find((item) => item.x === next.x && item.y === next.y && !collected.includes(item.id));
      if (found) {
        setCollected((items) => [...items, found.id]);
        setWorldMessage(`${found.sprite} ${found.effect}`);
      } else if (next.x === 11 && next.y === 0) {
        setWorldMessage(collected.length >= 4 ? `Mission complete! ${level.goal}` : "The destination is locked. Find at least four important objects first.");
      }
      return next;
    });
  }

  useEffect(() => {
    if (!worldOpen) return;
    function move(event: KeyboardEvent) {
      const moves: Record<string, [number, number]> = { ArrowUp: [0,-1], ArrowDown: [0,1], ArrowLeft: [-1,0], ArrowRight: [1,0], w: [0,-1], s: [0,1], a: [-1,0], d: [1,0] };
      const direction = moves[event.key];
      if (!direction) return;
      event.preventDefault();
      moveInWorld(...direction);
    }
    window.addEventListener("keydown", move);
    return () => window.removeEventListener("keydown", move);
  });

  function chooseBuilding(building: (typeof buildings)[number]) {
    setSelected(building);
  }

  function addCommand(command: Command) {
    if (commands.length < 8 && runState !== "running") {
      setCommands((current) => [...current, command]);
      setRunState("ready");
    }
  }

  async function runProgram() {
    if (!commands.length || runState === "running") return;
    setRunState("running");
    let next: Robot = { x: 0, y: 4, direction: 0 };
    setRobot(next);
    const steps = [[0, -1], [1, 0], [0, 1], [-1, 0]];
    for (const command of commands) {
      await new Promise((resolve) => setTimeout(resolve, 420));
      if (command === "left") next = { ...next, direction: (next.direction + 3) % 4 };
      if (command === "right") next = { ...next, direction: (next.direction + 1) % 4 };
      if (command === "forward") {
        const [dx, dy] = steps[next.direction];
        next = { ...next, x: next.x + dx, y: next.y + dy };
      }
      setRobot({ ...next });
    }
    const success = next.x === 2 && next.y === 2;
    setRunState(success ? "success" : "failed");
  }

  function resetProgram() {
    setCommands([]);
    setRobot({ x: 0, y: 4, direction: 0 });
    setRunState("ready");
  }

  return (
    <main className="portal-page">
      <header className="portal-topbar">
        <a href="/dashboard" className="portal-back">← Dashboard</a>
        <div className="portal-title">
          <span>Dear Adeline</span>
          <strong>AdelineMobile</strong>
        </div>
        <div className="portal-currency" aria-label="Learning record">
          <span>▤ {savedProjects.length} projects</span>
          <span>◈ Evidence first</span>
        </div>
      </header>

      <section className="adventure-journal" aria-label="Dear Adeline games">
        <header className="journal-intro"><span>YOUR ADVENTURE JOURNAL</span><h1>Choose one story worth entering.</h1><p>A few complete worlds will always beat a town full of empty doors.</p></header>
        <div className="journal-flourish" aria-hidden="true">❀ ─── ✦ ─── ❀</div>
        <article className="featured-adventure">
          <div className="featured-sketch" aria-hidden="true"><span>🚌</span><b>?</b><i>⚖</i><small>1955</small></div>
          <div className="featured-copy"><span>FEATURED INVESTIGATION · HISTORY & JUSTICE</span><h2>The Teenager History Nearly Forgot</h2><p>Walk through Montgomery, uncover four different kinds of historical records, and decide how courage became lasting change—and why one young person nearly disappeared from the famous version.</p><ul><li>Playable 2D investigation</li><li>About 30–45 minutes</li><li>Saves to your learning record</li></ul><button type="button" onClick={() => setInvestigationOpen(true)}>Open the case →</button></div>
        </article>
        <section className="journal-shelf" aria-label="More games"><header><span>MORE TO EXPLORE</span><p>Only playable work earns a place here.</p></header><div>
          <article className="shelf-card ready"><b>⌘</b><span>COMPUTER LAB</span><h3>Build Your First Arcade Game</h3><p>Learn the idea here, build a real game in MakeCode, then bring it back as evidence.</p><button type="button" onClick={() => setLabOpen(true)}>Enter the lab →</button></article>
          <article className="shelf-card next"><b>🌱</b><span>COMING NEXT</span><h3>The Water Has to Reach</h3><p>A greenhouse building and irrigation game using measurement and systems thinking.</p><small>In development</small></article>
          <article className="shelf-card next"><b>🧭</b><span>AFTER THAT</span><h3>Journey Through a Broken System</h3><p>A choice-driven journey where resources, policy, and human consequences collide.</p><small>Planned</small></article>
        </div></section>
      </section>

      {labOpen && (
        <section className="code-lab" aria-label="Codeworks Lab mission">
          <header>
            <button type="button" onClick={() => setLabOpen(false)}>← Town map</button>
            <div><span>COMPUTER LAB · MISSION 01</span><h1>Build Your First Arcade Game</h1></div>
            <strong>Evidence required for credit</strong>
          </header>

          <div className="lab-zones">
            <nav className="lab-zone-nav" aria-label="Computer Lab areas"><a href="#lab-adventure">Adventure</a><a href="#lab-arcade">Arcade</a><a href="#lab-maker">Maker Space</a><a href="#lab-cabinet">Portfolio Cabinet</a></nav>
            <section className="lab-zone" id="lab-adventure"><span>ADVENTURE · LEARN THE FOUNDATION</span><h2>First, wake the Garden Bot.</h2><p>An algorithm is a precise sequence of instructions. Computers follow exactly what you write—not what you meant. Guide the bot to the power cell, then use that same thinking in your own game.</p>
            <div className="lab-layout compact">
            <aside className="lab-brief"><span>QUICK PRACTICE</span><h2>The greenhouse sensors are dark.</h2><p>Build a sequence, run it, and debug it until the bot reaches the blue power cell.</p></aside>

            <div className="arcade-board">
              <div className="game-grid">
                {Array.from({ length: 25 }).map((_, index) => {
                  const x = index % 5;
                  const y = Math.floor(index / 5);
                  const isGoal = x === 2 && y === 2;
                  const isRobot = x === robot.x && y === robot.y;
                  return <div className={`grid-cell ${isGoal ? "goal" : ""}`} key={index}>{isGoal && "◆"}{isRobot && <span className={`garden-bot direction-${robot.direction}`}>▲</span>}</div>;
                })}
              </div>
              <div className={`run-message ${runState}`}>
                {runState === "ready" && "Build a program, then press RUN."}
                {runState === "running" && "Garden Bot is following your instructions…"}
                {runState === "failed" && "Not there yet. Trace each step and change the program."}
                {runState === "success" && "Power restored! Mission complete · ready to add to your learning record."}
              </div>
            </div>

            <aside className="block-editor">
              <span>COMMAND BLOCKS</span>
              <div className="command-tools">
                <button type="button" onClick={() => addCommand("forward")}>↑ Move forward</button>
                <button type="button" onClick={() => addCommand("left")}>↶ Turn left</button>
                <button type="button" onClick={() => addCommand("right")}>↷ Turn right</button>
              </div>
              <div className="program-stack">
                <b>ON START</b>
                {commands.length === 0 && <em>Tap command blocks to build your program.</em>}
                {commands.map((command, index) => <button type="button" key={`${command}-${index}`} onClick={() => setCommands((current) => current.filter((_, i) => i !== index))}>{index + 1}. {command === "forward" ? "Move forward" : command === "left" ? "Turn left" : "Turn right"}<span>×</span></button>)}
              </div>
              <div className="editor-actions"><button type="button" onClick={resetProgram}>Clear</button><button type="button" onClick={runProgram} disabled={!commands.length || runState === "running"}>▶ Run</button></div>
            </aside>
            </div></section>

            <section className="lab-zone arcade-zone" id="lab-arcade"><span>ARCADE · CURATED OUTSIDE TOOL</span><h2>Build it in Microsoft MakeCode Arcade.</h2><p>Create a playable game with a player, at least one enemy, a score, health or lives, and a clear win condition. MakeCode opens in a new tab so this mission stays here when you return.</p><a className="external-launch" href="https://arcade.makecode.com/" target="_blank" rel="noreferrer">Launch MakeCode Arcade ↗</a><small>Free browser-based tool. An outside service may have its own privacy terms and account options.</small></section>

            <section className="lab-zone maker-zone" id="lab-maker"><span>MAKER SPACE · BRING BACK WHAT YOU MADE</span><h2>Publish your game and return the share link.</h2><ol><li>In MakeCode, choose <b>Share</b> and publish the project.</li><li>Copy its MakeCode share link.</li><li>Paste it below and explain one design decision or bug you solved.</li></ol><form onSubmit={saveMakeCodeProject}><label>Game title<input value={projectTitle} onChange={(event) => setProjectTitle(event.target.value)} placeholder="Della's Chicken Escape" required /></label><label>MakeCode share link<input type="url" value={makeCodeUrl} onChange={(event) => setMakeCodeUrl(event.target.value)} placeholder="https://arcade.makecode.com/S..." required /></label><label>What did you build, change, or debug?<textarea value={projectExplanation} onChange={(event) => setProjectExplanation(event.target.value)} placeholder="My enemy moved too fast, so I changed…" required /></label><button type="submit">Add project to cabinet</button></form><p className="evidence-rule">Submitting a link does not automatically award credit. The playable project and explanation become reviewable evidence for Adeline’s competency check.</p></section>

            <section className="lab-zone cabinet-zone" id="lab-cabinet"><span>PORTFOLIO CABINET</span><h2>Student-made games live here.</h2>{savedProjects.length === 0 ? <p className="empty-cabinet">Your first published MakeCode game will appear here.</p> : <div className="project-cabinet">{savedProjects.map((project, index) => <article key={`${project.url}-${index}`}><b>PLAYABLE PROJECT</b><h3>{project.title}</h3><p>{project.explanation}</p><a href={project.url} target="_blank" rel="noreferrer">Play game ↗</a></article>)}</div>}</section>
          </div>
        </section>
      )}

      {worldOpen && (
        <section className="world-game" aria-label={`${level.title} 2D game`}>
          <header><button type="button" onClick={() => setWorldOpen(false)}>← Town map</button><div><span>2D LEARNING QUEST</span><h1>{level.title}</h1></div><strong>{collected.length}/6 found</strong></header>
          <div className="world-game-layout">
            <aside><span>YOUR MISSION</span><h2>{selected.name}</h2><p>{level.brief}</p><div className="world-inventory"><b>Backpack</b>{level.objects.map((item) => <i className={collected.includes(item.id) ? "found" : ""} key={item.id}>{collected.includes(item.id) ? item.sprite : "?"}<small>{collected.includes(item.id) ? item.label : "Unknown"}</small></i>)}</div></aside>
            <div className="world-stage" style={{ gridTemplateColumns: "repeat(12, 1fr)" }}>
              {Array.from({ length: 96 }).map((_, index) => {
                const x = index % 12, y = Math.floor(index / 12), key = `${x},${y}`;
                const object = level.objects.find((item) => item.x === x && item.y === y && !collected.includes(item.id));
                const isPlayer = worldPlayer.x === x && worldPlayer.y === y;
                const isGoal = x === 11 && y === 0;
                return <div className={`world-tile ${worldObstacles.has(key) ? "blocked" : ""} ${isGoal ? "destination" : ""}`} key={key}>{isGoal && level.goal}{object && <span title={object.label}>{object.sprite}</span>}{isPlayer && <b>{level.player}</b>}</div>;
              })}
            </div>
            <aside className="world-controls"><span>MOVE</span><div><button onClick={() => moveInWorld(0,-1)}>↑</button><button onClick={() => moveInWorld(-1,0)}>←</button><button onClick={() => moveInWorld(0,1)}>↓</button><button onClick={() => moveInWorld(1,0)}>→</button></div><p>{worldMessage}</p><button className="world-reset" onClick={() => void openWorld()}>Restart level</button></aside>
          </div>
        </section>
      )}

      {investigationOpen && <InvestigationGame onClose={() => setInvestigationOpen(false)} />}

      <nav className="portal-mobile-nav" aria-label="Game portal menu">
        <a href="/dashboard">⌂<span>Home</span></a>
        <button type="button">◇<span>Map</span></button>
        <button type="button">✦<span>Quests</span></button>
        <button type="button">◉<span>Friends</span></button>
        <button type="button">♙<span>Avatar</span></button>
      </nav>
    </main>
  );
}
