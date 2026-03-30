"use client";

/**
 * SketchnoteCanvas — HTML5 Canvas drawing surface for visual note-taking.
 * Tools: pen (black 2px), highlighter (yellow 50% opacity 12px), eraser, clear.
 * Supports pointer events for both mouse and touch.
 * Hint text shown when canvas is empty.
 */

import { useRef, useState, useEffect, useCallback } from "react";
import { Pencil, Highlighter, Eraser, Trash2, Download } from "lucide-react";

interface SketchnoteCanvasProps {
  lessonId: string;
  onSave?: (dataUrl: string) => void;
}

type Tool = "pen" | "highlighter" | "eraser";

const CANVAS_W = 700;
const CANVAS_H = 400;

const TOOL_CONFIG: Record<Tool, { lineWidth: number; strokeStyle: string; globalAlpha: number; globalCompositeOperation: GlobalCompositeOperation }> = {
  pen: {
    lineWidth: 2,
    strokeStyle: "#1a1a1a",
    globalAlpha: 1,
    globalCompositeOperation: "source-over",
  },
  highlighter: {
    lineWidth: 12,
    strokeStyle: "#FFE835",
    globalAlpha: 0.5,
    globalCompositeOperation: "source-over",
  },
  eraser: {
    lineWidth: 18,
    strokeStyle: "#ffffff",
    globalAlpha: 1,
    globalCompositeOperation: "destination-out",
  },
};

export function SketchnoteCanvas({ lessonId: _lessonId, onSave }: SketchnoteCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [tool, setTool] = useState<Tool>("pen");
  const [isEmpty, setIsEmpty] = useState(true);
  const drawing = useRef(false);

  // Fill white background on mount
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.fillStyle = "#FFFEF7";
    ctx.fillRect(0, 0, CANVAS_W, CANVAS_H);
  }, []);

  function applyTool(ctx: CanvasRenderingContext2D) {
    const cfg = TOOL_CONFIG[tool];
    ctx.lineWidth = cfg.lineWidth;
    ctx.strokeStyle = cfg.strokeStyle;
    ctx.globalAlpha = cfg.globalAlpha;
    ctx.globalCompositeOperation = cfg.globalCompositeOperation;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
  }

  function getPos(e: React.PointerEvent<HTMLCanvasElement>): [number, number] {
    const rect = canvasRef.current!.getBoundingClientRect();
    const scaleX = CANVAS_W / rect.width;
    const scaleY = CANVAS_H / rect.height;
    return [(e.clientX - rect.left) * scaleX, (e.clientY - rect.top) * scaleY];
  }

  const onPointerDown = useCallback((e: React.PointerEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    drawing.current = true;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d")!;
    applyTool(ctx);
    const [x, y] = getPos(e);
    ctx.beginPath();
    ctx.moveTo(x, y);
    setIsEmpty(false);
  }, [tool]); // eslint-disable-line react-hooks/exhaustive-deps

  const onPointerMove = useCallback((e: React.PointerEvent<HTMLCanvasElement>) => {
    if (!drawing.current) return;
    e.preventDefault();
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d")!;
    applyTool(ctx);
    const [x, y] = getPos(e);
    ctx.lineTo(x, y);
    ctx.stroke();
  }, [tool]); // eslint-disable-line react-hooks/exhaustive-deps

  const onPointerUp = useCallback((e: React.PointerEvent<HTMLCanvasElement>) => {
    e.preventDefault();
    drawing.current = false;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d")!;
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = "source-over";
  }, []);

  function handleClear() {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d")!;
    ctx.globalCompositeOperation = "source-over";
    ctx.globalAlpha = 1;
    ctx.fillStyle = "#FFFEF7";
    ctx.fillRect(0, 0, CANVAS_W, CANVAS_H);
    setIsEmpty(true);
  }

  function handleSave() {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const dataUrl = canvas.toDataURL("image/png");
    onSave?.(dataUrl);
  }

  const tools: { id: Tool; icon: React.ReactNode; label: string }[] = [
    { id: "pen",         icon: <Pencil size={15} />,      label: "Pen" },
    { id: "highlighter", icon: <Highlighter size={15} />, label: "Highlight" },
    { id: "eraser",      icon: <Eraser size={15} />,      label: "Eraser" },
  ];

  return (
    <div className="space-y-2">
      {/* Toolbar */}
      <div className="flex items-center gap-2 flex-wrap">
        {tools.map((t) => (
          <button
            key={t.id}
            onClick={() => setTool(t.id)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all"
            style={{
              background: tool === t.id ? "#2F4731" : "#F3F0EA",
              color: tool === t.id ? "#FFFEF7" : "#2F4731",
              border: tool === t.id ? "2px solid #2F4731" : "2px solid transparent",
            }}
          >
            {t.icon}
            {t.label}
          </button>
        ))}

        <button
          onClick={handleClear}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ml-auto"
          style={{ background: "#FEF2F2", color: "#9A3F4A", border: "2px solid transparent" }}
        >
          <Trash2 size={15} />
          Clear
        </button>
      </div>

      {/* Canvas wrapper */}
      <div className="relative rounded-xl overflow-hidden" style={{ border: "2px solid #E7DAC3" }}>
        <canvas
          ref={canvasRef}
          width={CANVAS_W}
          height={CANVAS_H}
          className="block w-full touch-none"
          style={{ cursor: tool === "eraser" ? "cell" : "crosshair", aspectRatio: `${CANVAS_W}/${CANVAS_H}` }}
          onPointerDown={onPointerDown}
          onPointerMove={onPointerMove}
          onPointerUp={onPointerUp}
          onPointerLeave={onPointerUp}
        />

        {/* Hint overlay — only when empty */}
        {isEmpty && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <span className="text-sm text-[#2F4731]/30 select-none" style={{ fontFamily: "var(--font-kalam), cursive" }}>
              Draw your notes here
            </span>
          </div>
        )}
      </div>

      {/* Save button */}
      {onSave && (
        <button
          onClick={handleSave}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-bold transition-all"
          style={{ background: "#BD6809", color: "#fff" }}
        >
          <Download size={15} />
          Save Sketchnote
        </button>
      )}
    </div>
  );
}
