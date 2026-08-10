"use client";

import { useEffect, useState } from "react";

type Command = "forward" | "left" | "right";
type Robot = { x: number; y: number; direction: number };

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
  const [commands, setCommands] = useState<Command[]>([]);
  const [robot, setRobot] = useState<Robot>({ x: 0, y: 4, direction: 0 });
  const [runState, setRunState] = useState<"ready" | "running" | "success" | "failed">("ready");

  function movePlayer(dx: number, dy: number) {
    setPlayer((current) => ({
      x: Math.max(5, Math.min(90, current.x + dx)),
      y: Math.max(8, Math.min(78, current.y + dy)),
    }));
  }

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (labOpen) return;
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
  }, [labOpen]);

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
        <div className="portal-currency" aria-label="Player progress">
          <span>✦ 1,840 XP</span>
          <span>◈ 12 tokens</span>
        </div>
      </header>

      <section className="portal-game">
        <div className="portal-map" aria-label="AdelineMobile learning town">
          <img className="portal-map-art" src="/adeline-town-map.png" alt="Hand-drawn learning town with paths and colorful buildings" />

          {buildings.map((building) => (
            <button
              className={`building-pin ${building.position} ${building.color} ${selected.id === building.id ? "selected" : ""}`}
              key={building.id}
              type="button"
              onClick={() => chooseBuilding(building)}
              aria-label={`Visit ${building.name}`}
            >
              <b>{building.icon}</b>
              <span>{building.name}</span>
            </button>
          ))}

          <div className="portal-player" style={{ left: `${player.x}%`, top: `${player.y}%` }} aria-label="Your movable avatar">
            <img src="/player-avatar.png" alt="Your avatar" />
            <span>YOU</span>
          </div>

          <div className="move-help"><span>Arrow keys move</span><div><i>↑</i><i>←</i><i>↓</i><i>→</i></div></div>

          <div className="touch-dpad" aria-label="Move avatar">
            <button type="button" onClick={() => movePlayer(0, -3)} aria-label="Move up">↑</button>
            <button type="button" onClick={() => movePlayer(-3, 0)} aria-label="Move left">←</button>
            <button type="button" onClick={() => movePlayer(0, 3)} aria-label="Move down">↓</button>
            <button type="button" onClick={() => movePlayer(3, 0)} aria-label="Move right">→</button>
          </div>

          <div className="portal-party" aria-label="Friends online">
            <p>PARTY · 3 ONLINE</p>
            <div><span>CR</span><span>DE</span><span>EL</span><button type="button" aria-label="Invite a friend">+</button></div>
          </div>

          <div className="world-event">
            <span>LIVE WORLD EVENT</span>
            <strong>The river is rising</strong>
            <p>Every district will feel what the town decides next.</p>
          </div>

          <article className="mission-card">
            <div className={`mission-icon ${selected.color}`}>{selected.icon}</div>
            <div className="mission-copy">
              <p>{selected.area}</p>
              <h1>{selected.name}</h1>
              <span>{selected.mission}</span>
              <strong>{selected.reward}</strong>
              <small>Adeline quietly maps completed work to your graduation record.</small>
            </div>
            {selected.id === "history" ? (
              <a className="mission-enter-link" href="/history">Enter the story →</a>
            ) : (
              <button type="button" disabled={selected.id !== "computer"} onClick={() => setLabOpen(true)}>
                {selected.id === "computer" ? "Enter the lab →" : "Coming soon"}
              </button>
            )}
          </article>
        </div>
      </section>

      {labOpen && (
        <section className="code-lab" aria-label="Codeworks Lab mission">
          <header>
            <button type="button" onClick={() => setLabOpen(false)}>← Town map</button>
            <div><span>CODEWORKS LAB · MISSION 01</span><h1>Wake the Garden Bot</h1></div>
            <strong>Debugging I · 180 XP</strong>
          </header>

          <div className="lab-layout">
            <aside className="lab-brief">
              <span>YOUR MISSION</span>
              <h2>The greenhouse sensors are dark.</h2>
              <p>Program the garden bot to reach the blue power cell. Build a sequence, run it, then debug it until it works.</p>
              <div className="concept-card"><b>What you’re learning</b><p>An algorithm is a precise sequence of instructions. Computers follow exactly what you write—not what you meant.</p></div>
            </aside>

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
          </div>
        </section>
      )}

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
