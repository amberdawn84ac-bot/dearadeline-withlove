"use client";

import { useEffect, useMemo, useState } from "react";
import type { PlayableGame } from "@/lib/brain-client";

export function InvestigationGame({ game, lessonId }: { game: PlayableGame; lessonId: string }) {
  const { interactive } = game;
  const [position, setPosition] = useState(interactive.player);
  const [collected, setCollected] = useState<string[]>([]);
  const obstacleKeys = useMemo(() => new Set(interactive.obstacles.map((item) => `${item.x}:${item.y}`)), [interactive.obstacles]);
  const won = collected.length >= interactive.required_objects && position.x === interactive.goal.x && position.y === interactive.goal.y;

  function move(dx: number, dy: number) {
    setPosition((current) => {
      const next = {
        x: Math.max(0, Math.min(interactive.world.width - 1, current.x + dx)),
        y: Math.max(0, Math.min(interactive.world.height - 1, current.y + dy)),
        sprite: current.sprite,
      };
      if (obstacleKeys.has(`${next.x}:${next.y}`)) return current;
      const found = interactive.objects.find((item) => item.x === next.x && item.y === next.y);
      if (found) setCollected((items) => items.includes(found.id) ? items : [...items, found.id]);
      return next;
    });
  }

  useEffect(() => {
    const keydown = (event: KeyboardEvent) => {
      const moves: Record<string, [number, number]> = { ArrowUp: [0, -1], ArrowDown: [0, 1], ArrowLeft: [-1, 0], ArrowRight: [1, 0] };
      const delta = moves[event.key];
      if (!delta) return;
      event.preventDefault();
      move(...delta);
    };
    window.addEventListener("keydown", keydown);
    return () => window.removeEventListener("keydown", keydown);
  });

  useEffect(() => {
    if (!won) return;
    window.dispatchEvent(new CustomEvent("adeline:learning-evidence", {
      detail: { lessonId, blockId: `game:${game.title}`, correct: true, evidenceType: "game_completion" },
    }));
  }, [game.title, lessonId, won]);

  const cells = Array.from({ length: interactive.world.width * interactive.world.height }, (_, index) => ({
    x: index % interactive.world.width,
    y: Math.floor(index / interactive.world.width),
  }));

  return <section className="rounded-[26px] border border-[#D9CFBC] bg-white p-5 md:p-7">
    <h2 className="text-3xl" style={{ fontFamily: "var(--font-emilys-candy), cursive" }}>{game.title}</h2>
    <p className="mt-2 text-sm text-[#2F4731]/70">{interactive.scenario}</p>
    <p className="mt-2 text-xs font-bold">Collect {interactive.required_objects} clue{interactive.required_objects === 1 ? "" : "s"}, then reach {interactive.goal.label}. Use the arrow keys or controls.</p>
    <div className="mx-auto mt-5 grid max-w-xl gap-1" style={{ gridTemplateColumns: `repeat(${interactive.world.width}, minmax(0, 1fr))` }} role="application" aria-label={game.title}>
      {cells.map((cell) => {
        const object = interactive.objects.find((item) => item.x === cell.x && item.y === cell.y && !collected.includes(item.id));
        const obstacle = interactive.obstacles.find((item) => item.x === cell.x && item.y === cell.y);
        const isPlayer = position.x === cell.x && position.y === cell.y;
        const isGoal = interactive.goal.x === cell.x && interactive.goal.y === cell.y;
        return <div key={`${cell.x}:${cell.y}`} className="grid aspect-square place-items-center rounded bg-[#F5EEDF] text-lg" aria-label={object?.label ?? (isGoal ? interactive.goal.label : undefined)}>{isPlayer ? interactive.player.sprite : object?.sprite ?? obstacle?.sprite ?? (isGoal ? "🏁" : "")}</div>;
      })}
    </div>
    <div className="mx-auto mt-4 grid w-36 grid-cols-3 gap-2">
      <span /><button type="button" onClick={() => move(0, -1)} className="rounded bg-[#2F4731] p-2 text-white" aria-label="Move up">↑</button><span />
      <button type="button" onClick={() => move(-1, 0)} className="rounded bg-[#2F4731] p-2 text-white" aria-label="Move left">←</button><button type="button" onClick={() => move(0, 1)} className="rounded bg-[#2F4731] p-2 text-white" aria-label="Move down">↓</button><button type="button" onClick={() => move(1, 0)} className="rounded bg-[#2F4731] p-2 text-white" aria-label="Move right">→</button>
    </div>
    <p className="mt-4 text-center text-sm font-bold">Clues: {collected.length}/{interactive.required_objects}</p>
    {won && <p className="mt-3 rounded-xl bg-[#E3ECDD] p-4 text-center font-bold">{interactive.success_message}</p>}
  </section>;
}
