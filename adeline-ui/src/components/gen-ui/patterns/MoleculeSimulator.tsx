"use client";

/**
 * MoleculeSimulator — Interactive 2D molecule / particle physics simulation.
 *
 * Students adjust temperature, observe particle behavior, and answer
 * comprehension questions. Uses HTML5 Canvas — zero external dependencies.
 * Designed for CREATION_SCIENCE track (states of matter, molecular motion).
 */

import { useRef, useEffect, useState, useCallback } from "react";
import { Play, Pause, RotateCcw, Thermometer, CheckCircle, FlaskConical } from "lucide-react";

export interface MoleculeSimulatorQuestion {
  id: string;
  text: string;
  options: string[];
  correctIndex: number;
}

export interface MoleculeSimulatorProps {
  title: string;
  description: string;
  substance?: string;
  questions?: MoleculeSimulatorQuestion[];
  onComplete?: (answers: Record<string, number>) => void;
  onStateChange?: (state: Record<string, any>) => void;
}

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  r: number;
}

const PARTICLE_COUNT = 40;
const CANVAS_W = 460;
const CANVAS_H = 220;

function makeParticles(temp: number): Particle[] {
  const speed = 0.3 + temp * 0.03;
  return Array.from({ length: PARTICLE_COUNT }, () => ({
    x: 20 + Math.random() * (CANVAS_W - 40),
    y: 20 + Math.random() * (CANVAS_H - 40),
    vx: (Math.random() - 0.5) * speed,
    vy: (Math.random() - 0.5) * speed,
    r: 6,
  }));
}

function stateOfMatter(temp: number): string {
  if (temp <= 30) return "Solid";
  if (temp <= 65) return "Liquid";
  return "Gas";
}

function stateColor(temp: number): string {
  if (temp <= 30) return "#60a5fa"; // blue
  if (temp <= 65) return "#34d399"; // green
  return "#f87171";                 // red
}

export function MoleculeSimulator({
  title,
  description,
  substance = "Water (H₂O)",
  questions = [],
  onComplete,
  onStateChange,
}: MoleculeSimulatorProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);
  const particlesRef = useRef<Particle[]>([]);
  const runningRef = useRef(true);

  const [temp, setTemp] = useState(50);
  const [running, setRunning] = useState(true);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [completed, setCompleted] = useState(false);
  const mountedAt = useRef(Date.now());

  const state = stateOfMatter(temp);
  const color = stateColor(temp);

  // Initialise / re-seed particles when temperature changes significantly
  useEffect(() => {
    particlesRef.current = makeParticles(temp);
  }, []);  // only on mount; velocity is updated each frame from temp

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d")!;

    const animate = () => {
      if (!runningRef.current) {
        animRef.current = requestAnimationFrame(animate);
        return;
      }

      ctx.clearRect(0, 0, CANVAS_W, CANVAS_H);

      // Background
      ctx.fillStyle = "#1e293b";
      ctx.fillRect(0, 0, CANVAS_W, CANVAS_H);

      // Draw bonds for solid/liquid
      if (temp <= 65) {
        ctx.strokeStyle = color + "40";
        ctx.lineWidth = 1;
        for (let i = 0; i < particlesRef.current.length; i++) {
          for (let j = i + 1; j < particlesRef.current.length; j++) {
            const a = particlesRef.current[i];
            const b = particlesRef.current[j];
            const dist = Math.hypot(a.x - b.x, a.y - b.y);
            const maxBond = temp <= 30 ? 28 : 40;
            if (dist < maxBond) {
              ctx.beginPath();
              ctx.moveTo(a.x, a.y);
              ctx.lineTo(b.x, b.y);
              ctx.stroke();
            }
          }
        }
      }

      const speedScale = 0.4 + temp * 0.025;
      const maxSpeed = speedScale * 2;

      for (const p of particlesRef.current) {
        // Normalise velocity toward target speed
        const speed = Math.hypot(p.vx, p.vy);
        if (speed > 0.01) {
          p.vx = (p.vx / speed) * speedScale + (Math.random() - 0.5) * 0.05;
          p.vy = (p.vy / speed) * speedScale + (Math.random() - 0.5) * 0.05;
        }

        // Clamp
        p.vx = Math.max(-maxSpeed, Math.min(maxSpeed, p.vx));
        p.vy = Math.max(-maxSpeed, Math.min(maxSpeed, p.vy));

        p.x += p.vx;
        p.y += p.vy;

        // Wall bounce
        if (p.x - p.r < 0) { p.x = p.r; p.vx *= -1; }
        if (p.x + p.r > CANVAS_W) { p.x = CANVAS_W - p.r; p.vx *= -1; }
        if (p.y - p.r < 0) { p.y = p.r; p.vy *= -1; }
        if (p.y + p.r > CANVAS_H) { p.y = CANVAS_H - p.r; p.vy *= -1; }

        // Draw particle
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();
        ctx.strokeStyle = "#fff2";
        ctx.lineWidth = 0.8;
        ctx.stroke();
      }

      animRef.current = requestAnimationFrame(animate);
    };

    animRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animRef.current);
  }, [temp, color]);

  const handleToggle = () => {
    runningRef.current = !runningRef.current;
    setRunning((r) => !r);
  };

  const handleReset = () => {
    particlesRef.current = makeParticles(temp);
    setTemp(50);
    setAnswers({});
    setCompleted(false);
    runningRef.current = true;
    setRunning(true);
    mountedAt.current = Date.now();
  };

  const handleAnswer = useCallback((qId: string, idx: number) => {
    const next = { ...answers, [qId]: idx };
    setAnswers(next);
    onStateChange?.({ temp, answers: next });
  }, [answers, temp, onStateChange]);

  const handleSubmit = () => {
    const responseTimeMs = Date.now() - mountedAt.current;
    setCompleted(true);
    onComplete?.(answers);
    onStateChange?.({ temp, answers, completed: true, responseTimeMs });
  };

  const allAnswered = questions.length === 0 || questions.every((q) => answers[q.id] !== undefined);

  return (
    <div
      className="rounded-2xl overflow-hidden"
      style={{ border: "2px solid #2F473130", background: "#0f172a" }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-3"
        style={{ background: "#1e293b", borderBottom: "1px solid #334155" }}
      >
        <div className="flex items-center gap-2">
          <FlaskConical size={15} style={{ color: "#BD6809" }} />
          <div>
            <p className="text-xs font-bold" style={{ color: "#f8fafc" }}>{title}</p>
            <p className="text-[10px]" style={{ color: "#94a3b8" }}>{substance}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleReset}
            className="flex items-center gap-1 px-2 py-1 rounded text-xs"
            style={{ background: "#334155", color: "#94a3b8" }}
            title="Reset simulation"
          >
            <RotateCcw size={11} />
            Reset
          </button>
          <button
            onClick={handleToggle}
            className="flex items-center gap-1 px-2 py-1 rounded text-xs font-bold"
            style={{ background: running ? "#2F4731" : "#BD6809", color: "#fff" }}
            title={running ? "Pause" : "Resume"}
          >
            {running ? <Pause size={11} /> : <Play size={11} />}
            {running ? "Pause" : "Play"}
          </button>
        </div>
      </div>

      {/* Description */}
      <div className="px-4 py-2" style={{ background: "#1e293b", borderBottom: "1px solid #334155" }}>
        <p className="text-xs leading-relaxed" style={{ color: "#94a3b8" }}>{description}</p>
      </div>

      {/* Canvas */}
      <canvas
        ref={canvasRef}
        width={CANVAS_W}
        height={CANVAS_H}
        className="w-full"
        style={{ display: "block" }}
        aria-label="Molecule simulation"
      />

      {/* Controls */}
      <div
        className="px-4 py-3 flex items-center gap-4"
        style={{ background: "#1e293b", borderTop: "1px solid #334155" }}
      >
        <Thermometer size={14} style={{ color: stateColor(temp) }} />
        <div className="flex-1">
          <input
            type="range"
            min={0}
            max={100}
            value={temp}
            onChange={(e) => setTemp(Number(e.target.value))}
            className="w-full accent-orange-500"
            aria-label="Temperature control"
          />
        </div>
        <div className="text-right min-w-[80px]">
          <p className="text-sm font-bold" style={{ color: stateColor(temp) }}>{state}</p>
          <p className="text-[10px]" style={{ color: "#64748b" }}>{temp}°</p>
        </div>
      </div>

      {/* Questions */}
      {questions.length > 0 && (
        <div
          className="px-4 py-4 space-y-4"
          style={{ background: "#0f172a", borderTop: "1px solid #1e293b" }}
        >
          {questions.map((q) => (
            <div key={q.id}>
              <p className="text-xs font-semibold mb-2" style={{ color: "#e2e8f0" }}>{q.text}</p>
              <div className="space-y-1.5">
                {q.options.map((opt, i) => {
                  const picked = answers[q.id] === i;
                  const isCorrect = completed && i === q.correctIndex;
                  const isWrong = completed && picked && i !== q.correctIndex;
                  return (
                    <button
                      key={i}
                      onClick={() => !completed && handleAnswer(q.id, i)}
                      disabled={completed}
                      className="w-full text-left text-xs px-3 py-2 rounded-lg transition-all"
                      style={{
                        background: isCorrect ? "#14532d" : isWrong ? "#450a0a" : picked ? "#1e3a5f" : "#1e293b",
                        border: `1.5px solid ${isCorrect ? "#22c55e" : isWrong ? "#ef4444" : picked ? "#3b82f6" : "#334155"}`,
                        color: "#e2e8f0",
                      }}
                    >
                      {opt}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Footer */}
      <div
        className="flex items-center justify-between px-4 py-3"
        style={{ background: "#1e293b", borderTop: "1px solid #334155" }}
      >
        <p className="text-[10px]" style={{ color: "#475569" }}>
          Drag the temperature slider to change molecular motion
        </p>
        {completed ? (
          <div className="flex items-center gap-1.5 text-xs font-bold" style={{ color: "#4ade80" }}>
            <CheckCircle size={14} />
            Submitted!
          </div>
        ) : questions.length > 0 ? (
          <button
            onClick={handleSubmit}
            disabled={!allAnswered}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold disabled:opacity-40 disabled:cursor-not-allowed"
            style={{ background: allAnswered ? "#BD6809" : "#334155", color: "#fff" }}
          >
            <CheckCircle size={13} />
            Submit
          </button>
        ) : null}
      </div>
    </div>
  );
}
