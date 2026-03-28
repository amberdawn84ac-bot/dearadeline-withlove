"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Sparkles, Send, Loader2 } from "lucide-react";
import { scaffold, generateLesson } from "@/lib/brain-client";
import type { Track, ScaffoldResponse, LessonResponse } from "@/lib/brain-client";

// ── Types ──────────────────────────────────────────────────────────────────────

interface Message {
  id: string;
  role: "user" | "adeline";
  content: string;
  zpd_zone?: string;
}

interface LessonContext {
  topic: string;
  track: Track;
  lessonId: string;
}

interface AdelineChatPanelProps {
  studentId?: string;
  gradeLevel?: string;
  activeLessonContext?: LessonContext | null;
  onLessonGenerated?: (lesson: LessonResponse) => void;
  onLessonRequest?: (topic: string) => void;
}

const STUDENT_ID = "demo-student-001";
const GRADE_LEVEL = "8";
const DEFAULT_TRACK: Track = "TRUTH_HISTORY";

const WELCOME_MSG: Message = {
  id: "welcome",
  role: "adeline",
  content:
    "Hello! I'm Adeline. Tell me a topic you'd like to explore and I'll find primary sources for you — or ask me questions about an active lesson.",
};

// ── ZPD zone badge colors ──────────────────────────────────────────────────────

function ZPDBadge({ zone }: { zone: string }) {
  const styles: Record<string, { bg: string; text: string; label: string }> = {
    FRUSTRATED: { bg: "#FEF2F2", text: "#991B1B", label: "Bridge" },
    IN_ZPD:     { bg: "#F0FDF4", text: "#166534", label: "Socratic" },
    BORED:      { bg: "#EFF6FF", text: "#1D4ED8", label: "Elevation" },
  };
  const s = styles[zone] ?? { bg: "#F9FAFB", text: "#374151", label: zone };
  return (
    <span
      style={{
        fontSize: 9,
        fontWeight: 800,
        background: s.bg,
        color: s.text,
        borderRadius: 4,
        padding: "2px 6px",
        letterSpacing: "0.08em",
        textTransform: "uppercase",
      }}
    >
      {s.label}
    </span>
  );
}

// ── AdelineChatPanel ───────────────────────────────────────────────────────────

export function AdelineChatPanel({
  studentId = STUDENT_ID,
  gradeLevel = GRADE_LEVEL,
  activeLessonContext,
  onLessonGenerated,
  onLessonRequest,
}: AdelineChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([WELCOME_MSG]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const addMessage = useCallback((msg: Omit<Message, "id">) => {
    setMessages((prev) => [
      ...prev,
      { ...msg, id: `${Date.now()}-${Math.random()}` },
    ]);
  }, []);

  const handleSend = useCallback(async () => {
    const text = input.trim();
    if (!text || isLoading) return;
    setInput("");
    addMessage({ role: "user", content: text });
    setIsLoading(true);

    try {
      if (activeLessonContext) {
        // Scaffold: student is responding to an active lesson
        const result: ScaffoldResponse = await scaffold({
          student_id: studentId,
          topic: activeLessonContext.topic,
          track: activeLessonContext.track,
          grade_level: gradeLevel,
          student_response: text,
        });
        addMessage({
          role: "adeline",
          content: result.adeline_response,
          zpd_zone: result.zpd_zone,
        });
      } else {
        // No active lesson — treat message as a lesson topic request
        const topic = text;
        addMessage({
          role: "adeline",
          content: `Searching the archive for verified sources on "${topic}"…`,
        });

        if (onLessonRequest) {
          onLessonRequest(topic);
        } else if (onLessonGenerated) {
          const lesson = await generateLesson({
            student_id: studentId,
            track: DEFAULT_TRACK,
            topic,
            is_homestead: false,
            grade_level: gradeLevel,
          });
          onLessonGenerated(lesson);
          addMessage({
            role: "adeline",
            content: `I found ${lesson.blocks.filter((b) => b.evidence[0]?.verdict === "VERIFIED").length} verified primary sources for "${lesson.title}". The lesson is ready in the panel.`,
          });
        }
      }
    } catch (err) {
      addMessage({
        role: "adeline",
        content:
          "The archive is temporarily unavailable. Please try again in a moment.",
      });
    } finally {
      setIsLoading(false);
    }
  }, [input, isLoading, activeLessonContext, studentId, gradeLevel, onLessonRequest, onLessonGenerated, addMessage]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full" style={{ background: "#FFFEF7" }}>
      {/* Header */}
      <div className="shrink-0 bg-[#2F4731] px-4 py-3 flex items-center gap-3">
        <div className="w-9 h-9 rounded-full bg-[#BD6809] flex items-center justify-center border-2 border-[#BD6809]/40 shrink-0">
          <span className="text-lg">🌿</span>
        </div>
        <div className="min-w-0">
          <h2
            className="text-sm font-bold text-white leading-tight truncate"
            style={{ fontFamily: "var(--font-emilys-candy), cursive" }}
          >
            Talking with Adeline
          </h2>
          <p className="text-xs text-white/60 leading-tight">
            {activeLessonContext
              ? `Lesson: ${activeLessonContext.topic}`
              : "Ask me anything"}
          </p>
        </div>
        <Sparkles className="w-4 h-4 text-[#BD6809] ml-auto shrink-0" />
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              style={{
                maxWidth: "85%",
                background: msg.role === "user" ? "#2F4731" : "#FDF6E9",
                color: msg.role === "user" ? "#FFFEF7" : "#2F4731",
                border: msg.role === "adeline" ? "1px solid #E7DAC3" : "none",
                borderRadius:
                  msg.role === "user"
                    ? "18px 18px 4px 18px"
                    : "18px 18px 18px 4px",
                padding: "10px 14px",
              }}
            >
              {msg.zpd_zone && (
                <div className="mb-1.5">
                  <ZPDBadge zone={msg.zpd_zone} />
                </div>
              )}
              <p className="text-sm leading-relaxed whitespace-pre-wrap">
                {msg.content}
              </p>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div
              style={{
                background: "#FDF6E9",
                border: "1px solid #E7DAC3",
                borderRadius: "18px 18px 18px 4px",
                padding: "10px 14px",
                display: "flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <Loader2 size={14} className="animate-spin text-[#BD6809]" />
              <span className="text-sm text-[#2F4731]/60 italic">
                Adeline is thinking…
              </span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div
        className="shrink-0 px-4 py-3 border-t border-[#E7DAC3]"
        style={{ background: "#FFFDF5" }}
      >
        <div className="flex items-end gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              activeLessonContext
                ? "Respond to the lesson…"
                : "Ask Adeline or enter a topic…"
            }
            rows={2}
            className="flex-1 resize-none rounded-xl px-3 py-2 text-sm text-[#2F4731] border border-[#E7DAC3] bg-white focus:outline-none focus:border-[#2F4731] transition-colors"
            style={{ lineHeight: "1.4" }}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="w-9 h-9 rounded-full flex items-center justify-center transition-all disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
            style={{ background: "#BD6809", color: "#FFF" }}
          >
            <Send size={15} />
          </button>
        </div>
        <p className="text-[10px] text-[#2F4731]/40 mt-1.5 text-center">
          Enter to send · Shift+Enter for new line
        </p>
      </div>
    </div>
  );
}
