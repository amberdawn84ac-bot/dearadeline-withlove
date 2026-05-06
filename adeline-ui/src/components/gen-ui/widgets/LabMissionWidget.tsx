"use client";

/**
 * LabMissionWidget
 *
 * Rendered when useChat receives a tool_call: render_lab_widget.
 * Displays a LAB_MISSION block as a Sovereign Lab recipe card with
 * parseable steps and a checklist for hands-on completion.
 *
 * Design: inherits PAPAYA/PARADISE/PALM palette. Chaos level gauge
 * mirrors the existing LabGuide.tsx visual language.
 */

import { useState } from "react";
import { FlaskConical, CheckSquare, Square, Leaf } from "lucide-react";

interface LabMissionWidgetProps {
  blockId: string;
  lessonId: string;
  track: string;
  title: string;
  content: string;
  isHomestead?: boolean;
}

interface ParsedLab {
  objective: string;
  materials: string[];
  steps: string[];
  connection: string | undefined;
}

/**
 * Parse a LAB_MISSION block content string.
 * Agent writes in a loose format:
 *   Objective: ...
 *   Materials: item1, item2, item3
 *   Steps:
 *   1. Do this first
 *   2. Then do this
 *   Connection: This demonstrates God's design in...
 */
function parseLabContent(content: string): ParsedLab {
  const lines = content
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);

  const objectiveLine = lines.find((l) => /^objective[:.]/i.test(l));
  const objective = objectiveLine
    ? objectiveLine.replace(/^objective[:.]\s*/i, "")
    : lines[0] ?? "Complete this hands-on experiment.";

  const materialsLine = lines.find((l) => /^materials[:.]/i.test(l));
  const materials = materialsLine
    ? materialsLine
        .replace(/^materials[:.]\s*/i, "")
        .split(/[,;]/)
        .map((m) => m.trim())
        .filter(Boolean)
    : [];

  const stepLines = lines.filter((l) => /^\d+[.)]\s/.test(l));
  const steps = stepLines.map((l) => l.replace(/^\d+[.)]\s*/, "").trim());

  const connectionLine = lines.find((l) =>
    /^(connection|creation connection)[:.]/i.test(l)
  );
  const connection = connectionLine
    ? connectionLine.replace(/^(connection|creation connection)[:.]\s*/i, "")
    : undefined;

  return {
    objective,
    materials,
    steps: steps.length > 0 ? steps : ["Follow the instructions in the lesson above."],
    connection,
  };
}

export function LabMissionWidget({
  blockId,
  lessonId,
  track,
  title,
  content,
  isHomestead = false,
}: LabMissionWidgetProps) {
  const parsed = parseLabContent(content);
  const [checked, setChecked] = useState<Record<number, boolean>>({});
  const [completed, setCompleted] = useState(false);
  const [callbackSent, setCallbackSent] = useState(false);

  const completedCount = Object.values(checked).filter(Boolean).length;
  const allDone = completedCount === parsed.steps.length;

  const toggleStep = (idx: number) => {
    setChecked((prev) => ({ ...prev, [idx]: !prev[idx] }));
  };

  const handleComplete = async () => {
    if (callbackSent) return;
    setCallbackSent(true);
    setCompleted(true);

    try {
      await fetch("/brain/genui/callback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          lesson_id: lessonId,
          component_type: "LAB_MISSION",
          event: "onComplete",
          block_id: blockId,
          track,
          state: { completedSteps: completedCount, totalSteps: parsed.steps.length },
        }),
      });
    } catch {
      // Non-fatal
    }
  };

  return (
    <div className="rounded-2xl border-2 border-[#E7DAC3] bg-[#FFFEF7] p-5 space-y-5 my-4 shadow-sm">
      {/* Header */}
      <div className="flex items-start gap-3">
        <div
          className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0"
          style={{ background: isHomestead ? "#FDF6E9" : "#F0FDF4" }}
        >
          {isHomestead ? (
            <Leaf className="w-5 h-5" style={{ color: "#BD6809" }} />
          ) : (
            <FlaskConical className="w-5 h-5" style={{ color: "#2F4731" }} />
          )}
        </div>
        <div>
          <p
            className="text-[10px] font-bold uppercase tracking-widest"
            style={{ color: isHomestead ? "#BD6809" : "#2F4731" }}
          >
            {isHomestead ? "Homestead Mission" : "Sovereign Lab"}
          </p>
          <p className="text-base font-bold text-[#2F4731] leading-tight">{title}</p>
        </div>
      </div>

      {/* Objective */}
      <p className="text-sm text-[#2F4731]/80 leading-relaxed italic border-l-4 border-[#E7DAC3] pl-3">
        {parsed.objective}
      </p>

      {/* Materials */}
      {parsed.materials.length > 0 && (
        <div>
          <p className="text-xs font-bold text-[#2F4731] uppercase tracking-wide mb-2">
            You'll need
          </p>
          <div className="flex flex-wrap gap-2">
            {parsed.materials.map((item, idx) => (
              <span
                key={idx}
                className="inline-block px-3 py-1 rounded-full text-xs font-medium bg-white border border-[#E7DAC3] text-[#2F4731]"
              >
                {item}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Steps checklist */}
      <div>
        <p className="text-xs font-bold text-[#2F4731] uppercase tracking-wide mb-3">
          Steps
        </p>
        <div className="space-y-2">
          {parsed.steps.map((step, idx) => (
            <button
              key={idx}
              onClick={() => toggleStep(idx)}
              className="w-full text-left flex items-start gap-3 rounded-xl px-4 py-3 transition-all"
              style={{
                background: checked[idx] ? "#F0FDF4" : "#FFFFFF",
                border: `1.5px solid ${checked[idx] ? "#28A745" : "#E7DAC3"}`,
              }}
            >
              {checked[idx] ? (
                <CheckSquare
                  className="w-4 h-4 mt-0.5 shrink-0"
                  style={{ color: "#28A745" }}
                />
              ) : (
                <Square
                  className="w-4 h-4 mt-0.5 shrink-0"
                  style={{ color: "#2F4731" }}
                />
              )}
              <span
                className="text-sm leading-relaxed"
                style={{
                  color: "#2F4731",
                  textDecoration: checked[idx] ? "line-through" : "none",
                  opacity: checked[idx] ? 0.6 : 1,
                }}
              >
                <span className="font-bold mr-1">{idx + 1}.</span>
                {step}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Creation connection */}
      {parsed.connection && (
        <div
          className="rounded-xl px-4 py-3 text-sm leading-relaxed"
          style={{
            background: "#FDF6E9",
            border: "1px solid #BD6809",
            color: "#2F4731",
          }}
        >
          <p className="text-[10px] font-bold uppercase tracking-widest text-[#BD6809] mb-1">
            God's Creation
          </p>
          {parsed.connection}
        </div>
      )}

      {/* Complete button */}
      {!completed ? (
        <button
          onClick={handleComplete}
          disabled={!allDone}
          className="w-full py-3 rounded-xl text-sm font-bold transition-all"
          style={{
            background: allDone ? "#2F4731" : "#F3F4F6",
            color: allDone ? "#FFFFFF" : "#9CA3AF",
            cursor: allDone ? "pointer" : "not-allowed",
          }}
        >
          {allDone
            ? "✓ Seal This Discovery"
            : `${completedCount} / ${parsed.steps.length} steps complete`}
        </button>
      ) : (
        <div
          className="w-full py-3 rounded-xl text-sm font-bold text-center"
          style={{ background: "#D4EDDA", color: "#166534" }}
        >
          ✓ Lab sealed — great work!
        </div>
      )}
    </div>
  );
}
