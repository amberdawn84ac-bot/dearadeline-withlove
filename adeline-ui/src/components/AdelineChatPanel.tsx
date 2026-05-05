"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Sparkles, Send, Loader2, FlaskConical, Search, Network, ListOrdered, Brain, Presentation } from "lucide-react";
import { scaffold, generateLesson, listProjects, getProject, reportActivity, streamConversation } from "@/lib/brain-client";
import type {
  Track, ScaffoldResponse, LessonResponse, LessonBlockResponse,
  ProjectSummary, ProjectDetail, ActivityReportResponse,
  ConversationMessage,
} from "@/lib/brain-client";
import { ProjectCatalog } from "@/components/projects/ProjectCard";
import { ProjectGuide } from "@/components/projects/ProjectGuide";
import RenderModeSelector from "@/components/RenderModeSelector";
import AnimatedSketchnoteRenderer from "@/components/gen-ui/patterns/AnimatedSketchnoteRenderer";
import type { LessonRenderMode, AnimatedSketchnoteLesson } from "@/lib/brain-client";

// ── Types ──────────────────────────────────────────────────────────────────────

type RichContent =
  | { type: "projectList"; projects: (ProjectSummary | ProjectDetail)[] }
  | { type: "projectDetail"; project: ProjectDetail }
  | { type: "activityCredit"; result: ActivityReportResponse };

type MessageSegment =
  | { type: "text"; content: string }
  | { type: "block"; data: Record<string, unknown> }

interface Message {
  id: string;
  role: "user" | "adeline";
  content: string;
  zpd_zone?: string;
  rich?: RichContent;
  segments?: MessageSegment[];
  streaming?: boolean;
}

interface LessonContext {
  topic: string;
  track: Track;
  lessonId: string;
}

interface AdelineChatPanelProps {
  studentId: string;
  gradeLevel: string;
  activeLessonContext?: LessonContext | null;
  onLessonGenerated?: (lesson: LessonResponse) => void;
  onLessonRequest?: (topic: string) => void;
  initialPrompt?: string | null;
  /** Text highlighted by the user for "Ask Adeline" feature */
  highlightedContext?: string | null;
  /** Callback to clear the highlighted context after it's been used */
  onHighlightedContextUsed?: () => void;
}

const DEFAULT_TRACK: Track = "TRUTH_HISTORY";

const WELCOME_MSG: Message = {
  id: "welcome",
  role: "adeline",
  content:
    "Hello! I'm Adeline. Tell me a topic you'd like to explore, ask to see projects, or tell me what you did today to earn credit.",
};

// ── Intent detection ───────────────────────────────────────────────────────────

const PROJECT_LIST_RE = /\b(show|browse|see|find|list|what|give me).{0,20}(project|craft|make|build|farm)/i;
const ACTIVITY_RE = /\b(i (spent|did|worked|practiced|baked|built|planted|made|helped|cooked|cleaned|studied|read|drew|painted|sewed|fixed)|today i|this (morning|afternoon|week)|i've been)\b/i;

/** Parse "2 hours", "30 minutes", "an hour" → minutes */
function parseMinutes(text: string): number {
  const hoursMatch = text.match(/(\d+(?:\.\d+)?)\s*hour/i);
  const minutesMatch = text.match(/(\d+)\s*min/i);
  const anHourMatch = /\ban hour\b/i.test(text);
  const halfHourMatch = /half.{0,5}hour/i.test(text);

  let total = 0;
  if (hoursMatch) total += parseFloat(hoursMatch[1]) * 60;
  if (minutesMatch) total += parseInt(minutesMatch[1]);
  if (anHourMatch && !hoursMatch) total += 60;
  if (halfHourMatch && !minutesMatch) total += 30;
  return total > 0 ? Math.round(total) : 60; // default 60 min
}

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

// ── Activity credit receipt ────────────────────────────────────────────────────

function ActivityCreditCard({ result }: { result: ActivityReportResponse }) {
  return (
    <div className="space-y-2 pt-1">
      <div
        className="rounded-xl p-3 space-y-2"
        style={{ background: "#F0FDF4", border: "1.5px solid #2F4731" }}
      >
        <p className="text-xs font-bold text-[#2F4731] uppercase tracking-wider">
          Credits recorded
        </p>
        <p className="text-sm font-bold text-[#2F4731]">{result.course_title}</p>
        <p className="text-xs text-[#2F4731]/70">{result.activity_description}</p>
        <div className="flex flex-wrap gap-2 pt-1 border-t border-[#2F4731]/20">
          <span className="text-xs font-bold text-[#BD6809]">
            {result.credit_hours} credit hr{result.credit_hours !== 1 ? "s" : ""}
          </span>
          {result.credited_tracks.map((ct) => (
            <span
              key={ct.track}
              className="text-[10px] px-2 py-0.5 rounded-full"
              style={{ backgroundColor: "rgba(47,71,49,0.08)", color: "#2F4731" }}
            >
              {ct.track.replace(/_/g, " ")} · {ct.credit_type}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

// ── Inline conversation block card ────────────────────────────────────────────

const BLOCK_CONFIGS: Record<string, { icon: string; bg: string; border: string; color: string; label: string }> = {
  PRIMARY_SOURCE:       { icon: "📜", bg: "#F0FDF4", border: "#166534",  color: "#166534",  label: "Primary Source" },
  LAB_MISSION:          { icon: "🧪", bg: "#FFF7ED", border: "#BD6809",  color: "#BD6809",  label: "Lab Mission" },
  LAB_GUIDE:            { icon: "📋", bg: "#FFF7ED", border: "#BD6809",  color: "#BD6809",  label: "Lab Guide" },
  EXPERIMENT:           { icon: "⚗️", bg: "#FFF7ED", border: "#BD6809",  color: "#BD6809",  label: "Experiment" },
  RESEARCH_MISSION:     { icon: "🔍", bg: "#FEFCE8", border: "#CA8A04",  color: "#CA8A04",  label: "Research Mission" },
  QUIZ:                 { icon: "📝", bg: "#EFF6FF", border: "#1D4ED8",  color: "#1D4ED8",  label: "Quiz" },
  TIMELINE:             { icon: "📅", bg: "#F5F3FF", border: "#6D28D9",  color: "#6D28D9",  label: "Timeline" },
  MIND_MAP:             { icon: "🕸️",  bg: "#ECFDF5", border: "#059669",  color: "#059669",  label: "Mind Map" },
  MNEMONIC:             { icon: "🧠", bg: "#FAF5FF", border: "#7C3AED",  color: "#7C3AED",  label: "Mnemonic" },
  SOCRATIC_DEBATE:      { icon: "💬", bg: "#FEF2F2", border: "#991B1B",  color: "#991B1B",  label: "Socratic Debate" },
  PROJECT_BUILDER:      { icon: "🔨", bg: "#FFF7ED", border: "#C2410C",  color: "#C2410C",  label: "Project" },
  NARRATED_SLIDE:       { icon: "🎞️",  bg: "#EFF6FF", border: "#2563EB",  color: "#2563EB",  label: "Slides" },
  SCAFFOLDED_PROBLEM:   { icon: "📐", bg: "#F5F3FF", border: "#7C3AED",  color: "#7C3AED",  label: "Problem" },
  HARD_THING_CHALLENGE: { icon: "🏔️",  bg: "#FEF2F2", border: "#DC2626",  color: "#DC2626",  label: "Challenge" },
  NARRATIVE:            { icon: "📖", bg: "#FDF6E9", border: "#E7DAC3",  color: "#2F4731",  label: "Narrative" },
};

function ConversationBlockCard({ block }: { block: Record<string, unknown> }) {
  const blockType = (block.block_type as string) ?? "NARRATIVE";
  const c = BLOCK_CONFIGS[blockType] ?? BLOCK_CONFIGS.NARRATIVE;
  const title   = block.title   as string | undefined;
  const content = block.content as string | undefined;

  return (
    <div
      className="rounded-xl px-4 py-3 space-y-1.5 my-2"
      style={{ background: c.bg, border: `1.5px solid ${c.border}` }}
    >
      <div className="flex items-center gap-2">
        <span role="img" aria-hidden>{c.icon}</span>
        <span className="text-[10px] font-bold uppercase tracking-wider" style={{ color: c.color }}>
          {c.label}
        </span>
      </div>
      {title   && <p className="text-xs font-semibold" style={{ color: c.color }}>{title}</p>}
      {content && <p className="text-sm leading-relaxed text-[#2F4731]">{content}</p>}
    </div>
  );
}

// ── AdelineChatPanel ───────────────────────────────────────────────────────────

export function AdelineChatPanel({
  studentId,
  gradeLevel,
  activeLessonContext,
  onLessonGenerated,
  onLessonRequest,
  initialPrompt,
  highlightedContext,
  onHighlightedContextUsed,
}: AdelineChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([WELCOME_MSG]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [initialPromptSent, setInitialPromptSent] = useState(false);
  const [conversationHistory, setConversationHistory] = useState<ConversationMessage[]>([]);
  const [pendingHighlight, setPendingHighlight] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Handle incoming highlighted context from TextSelectionMenu
  useEffect(() => {
    if (highlightedContext && highlightedContext !== pendingHighlight) {
      setPendingHighlight(highlightedContext);
      // Pre-fill input with a question about the highlighted text
      const truncated = highlightedContext.length > 100 
        ? highlightedContext.substring(0, 100) + "…" 
        : highlightedContext;
      setInput(`Can you explain this to me: "${truncated}"`);
      // Focus the input
      inputRef.current?.focus();
      // Notify parent that we've received the context
      onHighlightedContextUsed?.();
    }
  }, [highlightedContext, pendingHighlight, onHighlightedContextUsed]);

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
      } else if (PROJECT_LIST_RE.test(text)) {
        // Project catalog intent
        addMessage({ role: "adeline", content: "Let me pull up the project catalog for you…" });
        const { projects } = await listProjects({}, "STUDENT");
        addMessage({
          role: "adeline",
          content: "",
          rich: { type: "projectList", projects },
        });
      } else if (ACTIVITY_RE.test(text)) {
        // Life-to-credit: student describing what they did
        const minutes = parseMinutes(text);
        addMessage({ role: "adeline", content: "Got it — let me calculate your credits…" });
        const result = await reportActivity(
          { student_id: studentId, grade_level: gradeLevel, description: text, time_minutes: minutes },
          "STUDENT",
        );
        addMessage({
          role: "adeline",
          content: result.adeline_note,
          rich: { type: "activityCredit", result },
        });
      } else {
        // Default: streaming conversation
        const streamingId = `${Date.now()}-${Math.random()}`;
        setMessages((prev) => [
          ...prev,
          { id: streamingId, role: "adeline", content: "", segments: [], streaming: true },
        ]);

        let textBuffer = "";

        try {
          for await (const event of streamConversation({
            studentId,
            message: text,
            gradeLevel,
            history: conversationHistory,
          })) {
            if (event.type === "text") {
              textBuffer += event.delta;
              setMessages((prev) =>
                prev.map((m) => {
                  if (m.id !== streamingId) return m;
                  const segs = m.segments ? [...m.segments] : [];
                  const last = segs[segs.length - 1];
                  if (last?.type === "text") {
                    segs[segs.length - 1] = { type: "text", content: last.content + event.delta };
                  } else {
                    segs.push({ type: "text", content: event.delta });
                  }
                  return { ...m, content: textBuffer, segments: segs };
                })
              );
            } else if (event.type === "block") {
              // eslint-disable-next-line @typescript-eslint/no-unused-vars
              const { type: _t, ...blockData } = event;
              setMessages((prev) =>
                prev.map((m) => {
                  if (m.id !== streamingId) return m;
                  return {
                    ...m,
                    segments: [...(m.segments ?? []), { type: "block" as const, data: blockData as Record<string, unknown> }],
                  };
                })
              );
            } else if (event.type === "zpd") {
              setMessages((prev) =>
                prev.map((m) => m.id === streamingId ? { ...m, zpd_zone: event.zone } : m)
              );
            } else if (event.type === "done") {
              setMessages((prev) =>
                prev.map((m) => m.id === streamingId ? { ...m, streaming: false } : m)
              );
            } else if (event.type === "error") {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === streamingId
                    ? { ...m, content: event.message, streaming: false }
                    : m
                )
              );
            }
          }
        } catch {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === streamingId
                ? { ...m, content: "The archive is temporarily unavailable. Please try again in a moment.", streaming: false }
                : m
            )
          );
        }

        setConversationHistory((prev) => [
          ...prev,
          { role: "user", content: text },
          { role: "adeline", content: textBuffer },
        ]);
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
  }, [input, isLoading, activeLessonContext, studentId, gradeLevel, onLessonRequest, onLessonGenerated, addMessage, conversationHistory]);

  // Auto-send initial prompt (e.g. from Daily Bread "Start Deep Dive Study")
  useEffect(() => {
    if (initialPrompt && !initialPromptSent && studentId) {
      setInitialPromptSent(true);
      setInput(initialPrompt);
      // Defer to next tick so input state is set before send
      setTimeout(() => {
        setInput('');
        addMessage({ role: 'user', content: initialPrompt });
        setIsLoading(true);
        // Trigger the same flow as handleSend by calling the generate endpoint
        (async () => {
          try {
            const lesson = await generateLesson({
              student_id: studentId,
              topic: initialPrompt,
              track: 'DISCIPLESHIP' as Track,
              grade_level: gradeLevel,
              is_homestead: false,
            });
            addMessage({ role: 'adeline', content: lesson.title || 'Here is your Daily Bread study.' });
            onLessonGenerated?.(lesson);
          } catch {
            addMessage({ role: 'adeline', content: 'The archive is temporarily unavailable. Please try again in a moment.' });
          } finally {
            setIsLoading(false);
          }
        })();
      }, 100);
    }
  }, [initialPrompt, initialPromptSent, studentId, gradeLevel, addMessage, onLessonGenerated]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleProjectSelect = useCallback(async (projectId: string) => {
    addMessage({ role: "user", content: `I'd like to do that project.` });
    setIsLoading(true);
    try {
      const project = await getProject(projectId, "STUDENT");
      addMessage({
        role: "adeline",
        content: `Here's your step-by-step guide for **${project.title}**:`,
        rich: { type: "projectDetail", project },
      });
    } catch {
      addMessage({ role: "adeline", content: "I couldn't load that project right now. Please try again." });
    } finally {
      setIsLoading(false);
    }
  }, [addMessage]);

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
                maxWidth: msg.rich ? "100%" : "85%",
                width: msg.rich ? "100%" : undefined,
                background: msg.role === "user" ? "#2F4731" : "#FDF6E9",
                color: msg.role === "user" ? "#FFFEF7" : "#2F4731",
                border: msg.role === "adeline" ? "1px solid #E7DAC3" : "none",
                borderRadius:
                  msg.role === "user"
                    ? "18px 18px 4px 18px"
                    : "18px 18px 18px 4px",
                padding: msg.rich ? "12px" : "10px 14px",
              }}
            >
              {/* Streaming conversation message */}
              {msg.segments !== undefined ? (
                <div className="space-y-0">
                  {msg.zpd_zone && (
                    <div className="mb-1.5">
                      <ZPDBadge zone={msg.zpd_zone} />
                    </div>
                  )}
                  {msg.segments.length === 0 && msg.streaming ? (
                    <div className="flex items-center gap-1.5">
                      <Loader2 size={12} className="animate-spin text-[#BD6809]" />
                      <span className="text-sm text-[#2F4731]/50 italic">…</span>
                    </div>
                  ) : (
                    msg.segments.map((seg, i) =>
                      seg.type === "text" ? (
                        <p key={i} className="text-sm leading-relaxed whitespace-pre-wrap mb-2">
                          {seg.content}
                          {msg.streaming && i === msg.segments!.length - 1 && (
                            <span
                              className="inline-block w-1.5 h-3.5 ml-0.5 rounded-sm align-middle animate-pulse"
                              style={{ background: "#BD6809" }}
                            />
                          )}
                        </p>
                      ) : (
                        <ConversationBlockCard key={i} block={seg.data} />
                      )
                    )
                  )}
                </div>
              ) : (
                <>
                  {msg.zpd_zone && (
                    <div className="mb-1.5">
                      <ZPDBadge zone={msg.zpd_zone} />
                    </div>
                  )}
                  {msg.content && (
                    <p className="text-sm leading-relaxed whitespace-pre-wrap mb-2">
                      {msg.content}
                    </p>
                  )}

                  {/* Rich content */}
                  {msg.rich?.type === "projectList" && (
                    <ProjectCatalog
                      projects={msg.rich.projects}
                      onSelect={handleProjectSelect}
                    />
                  )}
                  {msg.rich?.type === "projectDetail" && (
                    <ProjectGuide
                      projectId={msg.rich.project.id}
                      studentId={studentId}
                      onSeal={() => {
                        // Project sealed — refresh student state if needed
                      }}
                    />
                  )}
                  {msg.rich?.type === "activityCredit" && (
                    <ActivityCreditCard result={msg.rich.result} />
                  )}
                </>
              )}
            </div>
          </div>
        ))}

        {isLoading && !messages.some((m) => m.streaming) && (
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
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              pendingHighlight
                ? "Ask about the highlighted text…"
                : activeLessonContext
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

// ── LessonBlockChatPanel ───────────────────────────────────────────────────────
// A separate lesson panel: topic + track picker → blocks rendered as chat bubbles.

const TRACK_OPTIONS: { value: Track; label: string }[] = [
  { value: "TRUTH_HISTORY",        label: "History" },
  { value: "CREATION_SCIENCE",     label: "Science" },
  { value: "HOMESTEADING",         label: "Homestead" },
  { value: "GOVERNMENT_ECONOMICS", label: "Govt" },
  { value: "JUSTICE_CHANGEMAKING", label: "Justice" },
  { value: "DISCIPLESHIP",         label: "Discipleship" },
  { value: "HEALTH_NATUROPATHY",   label: "Health" },
  { value: "ENGLISH_LITERATURE",   label: "English" },
];

interface LessonBlockChatPanelProps {
  studentId: string;
  initialTrack?: Track;
}

function BlockBubble({ block }: { block: LessonBlockResponse }) {
  const verdict = block.evidence[0]?.verdict ?? "ARCHIVE_SILENT";
  const sourceTitle = block.evidence[0]?.source_title;

  if (block.is_silenced || verdict === "ARCHIVE_SILENT") {
    return (
      <div
        className="max-w-[88%] rounded-2xl rounded-bl-sm px-4 py-3 space-y-1 animate-fade-slide-in"
        style={{ background: "#F3F4F6", border: "1px solid #D1D5DB" }}
      >
        <p className="text-[10px] font-semibold text-[#6B7280] uppercase tracking-wide">
          Source not found
        </p>
        <p className="text-sm text-[#374151] leading-relaxed">{block.content}</p>
      </div>
    );
  }

  if (block.block_type === "EXPERIMENT" || block.block_type === "LAB_MISSION") {
    return (
      <div
        className="max-w-[88%] rounded-2xl rounded-bl-sm px-4 py-3 space-y-1.5 animate-fade-slide-in"
        style={{ background: "#FFF7ED", border: "2px solid #BD6809" }}
      >
        <div className="flex items-center gap-1.5">
          <FlaskConical size={13} className="text-[#BD6809]" />
          <span className="text-[10px] font-bold text-[#BD6809] uppercase tracking-wide">
            Experiment
          </span>
        </div>
        <p className="text-sm text-[#2F4731] leading-relaxed">{block.content}</p>
      </div>
    );
  }

  if (verdict === "RESEARCH_MISSION") {
    return (
      <div
        className="max-w-[88%] rounded-2xl rounded-bl-sm px-4 py-3 space-y-1.5 animate-fade-slide-in"
        style={{ background: "#FEFCE8", border: "2px solid #CA8A04" }}
      >
        <div className="flex items-center gap-1.5">
          <Search size={13} className="text-[#CA8A04]" />
          <span className="text-[10px] font-bold text-[#CA8A04] uppercase tracking-wide">
            Research Mission
          </span>
        </div>
        <p className="text-sm text-[#2F4731] leading-relaxed">{block.content}</p>
      </div>
    );
  }

  if (block.block_type === "MIND_MAP") return (
    <div className="flex items-center gap-2 text-xs px-3 py-2 rounded-lg border border-green-700 bg-green-50 text-green-800">
      <Network size={13} /> Mind Map: {block.mind_map_data?.concept}
    </div>
  );
  if (block.block_type === "TIMELINE") return (
    <div className="flex items-center gap-2 text-xs px-3 py-2 rounded-lg border border-[#1E3A5F] bg-blue-50 text-[#1E3A5F]">
      <ListOrdered size={13} /> Timeline: {block.timeline_data?.span} · {block.timeline_data?.events.length} events
    </div>
  );
  if (block.block_type === "MNEMONIC") return (
    <div className="flex items-center gap-2 text-xs px-3 py-2 rounded-lg border border-violet-700 bg-violet-50 text-violet-800">
      <Brain size={13} /> Remember: {block.mnemonic_data?.acronym}
    </div>
  );
  if (block.block_type === "NARRATED_SLIDE") return (
    <div className="flex items-center gap-2 text-xs px-3 py-2 rounded-lg border border-blue-700 bg-blue-50 text-blue-800">
      <Presentation size={13} /> {block.narrated_slide_data?.slides.length} Slides · {block.narrated_slide_data?.total_duration_minutes} min
    </div>
  );

  // VERIFIED
  return (
    <div
      className="max-w-[88%] rounded-2xl rounded-bl-sm px-4 py-3 space-y-2 animate-fade-slide-in"
      style={{ background: "#fff", border: "1px solid #E7DAC3" }}
    >
      {sourceTitle && (
        <div className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-green-500 shrink-0" />
          <span className="text-[10px] font-semibold text-[#166534] truncate">{sourceTitle}</span>
        </div>
      )}
      <p className="text-sm text-[#2F4731] leading-relaxed">{block.content}</p>
    </div>
  );
}

export function LessonBlockChatPanel({ studentId, initialTrack = "TRUTH_HISTORY" }: LessonBlockChatPanelProps) {
  const [topic, setTopic] = useState("");
  const [track, setTrack] = useState<Track>(initialTrack);
  const [renderMode, setRenderMode] = useState<LessonRenderMode>("standard_lesson");
  const [blocks, setBlocks] = useState<LessonBlockResponse[]>([]);
  const [animatedLesson, setAnimatedLesson] = useState<AnimatedSketchnoteLesson | null>(null);
  const [visibleCount, setVisibleCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Reveal blocks one at a time with a short delay for the "streaming" feel
  useEffect(() => {
    if (visibleCount >= blocks.length) return;
    const timer = setTimeout(() => setVisibleCount((c) => c + 1), 600);
    return () => clearTimeout(timer);
  }, [visibleCount, blocks.length]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [visibleCount, loading]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!topic.trim() || loading) return;
    setBlocks([]);
    setAnimatedLesson(null);
    setVisibleCount(0);
    setLoading(true);

    if (renderMode === "animated_sketchnote_lesson") {
      try {
        const res = await fetch("/api/adeline/animated-lesson", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ topic: topic.trim(), duration_seconds: 180 }),
        });
        if (res.ok) {
          const data = await res.json();
          setAnimatedLesson(data as AnimatedSketchnoteLesson);
        }
      } catch {
        // surface nothing — user can retry
      } finally {
        setLoading(false);
      }
      return;
    }

    try {
      const lesson: LessonResponse = await generateLesson({
        student_id: studentId,
        track,
        topic: topic.trim(),
        is_homestead: false,
        grade_level: "9",
      });
      setBlocks(lesson.blocks);
    } catch {
      // surface nothing — user can retry
    } finally {
      setLoading(false);
    }
  }

  const visibleBlocks = blocks.slice(0, visibleCount);
  const stillStreaming = visibleCount < blocks.length && blocks.length > 0;

  return (
    <div className="flex flex-col h-full" style={{ background: "#FFFEF7" }}>
      {/* Render mode selector */}
      <div className="shrink-0 px-4 pt-4 pb-1">
        <RenderModeSelector value={renderMode} onChange={setRenderMode} disabled={loading} />
      </div>

      {/* Track selector */}
      <div className="shrink-0 px-4 pt-2 pb-2">
        <div className="flex gap-1.5 flex-wrap">
          {TRACK_OPTIONS.map((t) => (
            <button
              key={t.value}
              onClick={() => setTrack(t.value)}
              className="px-3 py-1 rounded-full text-xs font-semibold transition-all"
              style={{
                background: track === t.value ? "#2F4731" : "#F3F0EA",
                color: track === t.value ? "#FFFEF7" : "#2F4731",
              }}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        {/* Animated sketchnote output */}
        {animatedLesson && (
          <AnimatedSketchnoteRenderer lesson={animatedLesson} />
        )}

        {visibleBlocks.map((block) => (
          <div key={block.block_id} className="flex justify-start">
            <BlockBubble block={block} />
          </div>
        ))}

        {/* Typing indicator between blocks or during fetch */}
        {(loading || stillStreaming) && (
          <div className="flex justify-start">
            <div
              className="rounded-2xl rounded-bl-sm px-4 py-3 flex items-center gap-2"
              style={{ background: "#FDF6E9", border: "1px solid #E7DAC3" }}
            >
              <Loader2 size={14} className="animate-spin text-[#BD6809]" />
              <span className="text-sm text-[#2F4731]/60 italic">Adeline is thinking…</span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Topic input */}
      <div className="shrink-0 px-4 py-3 border-t border-[#E7DAC3]" style={{ background: "#FFFDF5" }}>
        <form onSubmit={handleSubmit} className="flex items-end gap-2">
          <input
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="Enter a topic to explore…"
            className="flex-1 rounded-xl px-3 py-2 text-sm text-[#2F4731] border border-[#E7DAC3] bg-white focus:outline-none focus:border-[#2F4731] transition-colors"
          />
          <button
            type="submit"
            disabled={!topic.trim() || loading}
            className="w-9 h-9 rounded-full flex items-center justify-center transition-all disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
            style={{ background: "#BD6809", color: "#fff" }}
          >
            <Send size={15} />
          </button>
        </form>
      </div>
    </div>
  );
}
