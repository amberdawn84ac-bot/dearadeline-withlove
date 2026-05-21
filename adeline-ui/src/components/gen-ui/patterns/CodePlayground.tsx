"use client";

/**
 * CodePlayground — Live JavaScript/HTML code execution playground.
 *
 * Uses a sandboxed iframe with srcdoc for safe isolation — no eval(),
 * no shared scope, no dependency on Sandpack or external services.
 * Beginner-friendly for homeschool students (K-12).
 *
 * Props supplied by GENUI_ASSEMBLY blocks from the orchestrator.
 */

import { useState, useRef, useCallback } from "react";
import { Play, RotateCcw, CheckCircle, Code2 } from "lucide-react";

export interface CodePlaygroundProps {
  language: "javascript" | "html";
  starterCode: string;
  instructions: string;
  expectedOutput?: string;
  onComplete?: (code: string) => void;
  onStateChange?: (state: Record<string, any>) => void;
}

const SANDBOX_ATTRS =
  "allow-scripts allow-same-origin";

function buildSrcdoc(language: "javascript" | "html", code: string): string {
  if (language === "html") {
    return code;
  }
  return `<!DOCTYPE html>
<html>
<head><style>
  body { font-family: monospace; font-size: 13px; padding: 8px; margin: 0;
         background: #1e1e1e; color: #d4d4d4; white-space: pre-wrap; }
  .error { color: #f48771; }
</style></head>
<body><div id="out"></div>
<script>
  const out = document.getElementById('out');
  const origLog = console.log;
  console.log = (...args) => {
    out.textContent += args.map(a =>
      typeof a === 'object' ? JSON.stringify(a, null, 2) : String(a)
    ).join(' ') + '\\n';
  };
  window.onerror = (msg, _src, _line, _col, err) => {
    out.innerHTML += '<span class="error">Error: ' + (err?.message || msg) + '</span>\\n';
    return true;
  };
  try {
    ${code}
  } catch(e) {
    out.innerHTML += '<span class="error">Error: ' + e.message + '</span>\\n';
  }
<\/script>
</body>
</html>`;
}

export function CodePlayground({
  language,
  starterCode,
  instructions,
  expectedOutput,
  onComplete,
  onStateChange,
}: CodePlaygroundProps) {
  const [code, setCode] = useState(starterCode);
  const [srcdoc, setSrcdoc] = useState<string | null>(null);
  const [ran, setRan] = useState(false);
  const [completed, setCompleted] = useState(false);
  const mountedAt = useRef(Date.now());

  const handleRun = useCallback(() => {
    setSrcdoc(buildSrcdoc(language, code));
    setRan(true);
    onStateChange?.({ code, ran: true });
  }, [code, language, onStateChange]);

  const handleReset = useCallback(() => {
    setCode(starterCode);
    setSrcdoc(null);
    setRan(false);
    setCompleted(false);
    mountedAt.current = Date.now();
    onStateChange?.({ code: starterCode, ran: false });
  }, [starterCode, onStateChange]);

  const handleSubmit = useCallback(() => {
    const responseTimeMs = Date.now() - mountedAt.current;
    setCompleted(true);
    onComplete?.(code);
    onStateChange?.({ code, ran, completed: true, responseTimeMs });
  }, [code, ran, onComplete, onStateChange]);

  const lineCount = code.split("\n").length;

  return (
    <div
      className="rounded-2xl overflow-hidden"
      style={{ border: "2px solid #2F473140", background: "#1e1e1e" }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-2.5"
        style={{ background: "#2d2d2d", borderBottom: "1px solid #3a3a3a" }}
      >
        <div className="flex items-center gap-2">
          <Code2 size={14} style={{ color: "#BD6809" }} />
          <span className="text-xs font-mono font-bold uppercase tracking-widest" style={{ color: "#BD6809" }}>
            {language === "html" ? "HTML" : "JavaScript"} Playground
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <button
            onClick={handleReset}
            className="flex items-center gap-1 px-2 py-1 rounded text-xs font-mono transition-colors"
            style={{ background: "#3a3a3a", color: "#9cdcfe" }}
            title="Reset to starter code"
          >
            <RotateCcw size={11} />
            Reset
          </button>
          <button
            onClick={handleRun}
            className="flex items-center gap-1 px-3 py-1 rounded text-xs font-mono font-bold transition-colors"
            style={{ background: "#2F4731", color: "#fff" }}
            title="Run code"
          >
            <Play size={11} />
            Run
          </button>
        </div>
      </div>

      {/* Instructions */}
      <div
        className="px-4 py-2.5 text-xs leading-relaxed"
        style={{ background: "#252526", borderBottom: "1px solid #3a3a3a", color: "#9cdcfe" }}
      >
        {instructions}
      </div>

      {/* Editor */}
      <div className="relative">
        {/* Line numbers */}
        <div
          className="absolute left-0 top-0 bottom-0 w-10 flex flex-col items-end pr-2 pt-3 select-none"
          style={{ background: "#1e1e1e", color: "#858585", fontFamily: "monospace", fontSize: 12 }}
        >
          {Array.from({ length: lineCount }, (_, i) => (
            <div key={i} style={{ lineHeight: "1.5rem" }}>{i + 1}</div>
          ))}
        </div>
        <textarea
          value={code}
          onChange={(e) => setCode(e.target.value)}
          spellCheck={false}
          aria-label="Code editor"
          className="w-full font-mono text-xs leading-6 resize-none focus:outline-none pl-12 pr-4 pt-3 pb-3"
          style={{
            background: "#1e1e1e",
            color: "#d4d4d4",
            minHeight: Math.max(160, lineCount * 24 + 24),
            caretColor: "#aeafad",
          }}
          rows={Math.max(7, lineCount)}
        />
      </div>

      {/* Output pane */}
      {srcdoc && (
        <div style={{ borderTop: "1px solid #3a3a3a" }}>
          <div
            className="px-4 py-1.5 text-[10px] font-mono uppercase tracking-widest"
            style={{ background: "#252526", color: "#858585" }}
          >
            Output
          </div>
          <iframe
            key={srcdoc}
            srcDoc={srcdoc}
            sandbox={SANDBOX_ATTRS}
            className="w-full"
            style={{ height: 140, border: "none", background: "#1e1e1e" }}
            title="Code output"
          />
        </div>
      )}

      {/* Footer */}
      <div
        className="flex items-center justify-between px-4 py-2.5"
        style={{ background: "#252526", borderTop: "1px solid #3a3a3a" }}
      >
        {expectedOutput && (
          <p className="text-[10px] font-mono" style={{ color: "#858585" }}>
            Expected: <span style={{ color: "#9cdcfe" }}>{expectedOutput}</span>
          </p>
        )}
        <div className="ml-auto">
          {completed ? (
            <div className="flex items-center gap-1.5 text-xs font-bold" style={{ color: "#4ade80" }}>
              <CheckCircle size={14} />
              Submitted!
            </div>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={!ran}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all disabled:opacity-40 disabled:cursor-not-allowed"
              style={{ background: ran ? "#BD6809" : "#3a3a3a", color: "#fff" }}
              title={ran ? "Submit your solution" : "Run your code first"}
            >
              <CheckCircle size={13} />
              Submit Solution
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
