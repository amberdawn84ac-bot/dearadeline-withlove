"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Sparkles, Send, Loader2 } from "lucide-react";
import { scaffold, listProjects, getProject, reportActivity, streamConversation, uploadActivityEvidence, getLearningPlan } from "@/lib/brain-client";
import type {
  Track, ScaffoldResponse,
  ProjectSummary, ProjectDetail, ActivityReportResponse,
  ConversationMessage,
} from "@/lib/brain-client";
import { ProjectCatalog } from "@/components/projects/ProjectCard";
import { ProjectGuide } from "@/components/projects/ProjectGuide";
import { useALUStream } from "@/hooks/useALUStream";
import { StreamingGenUIRenderer } from "@/components/gen-ui/StreamingGenUIRenderer";
import { parseDataStreamLine } from "@/lib/stream-protocol";

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
  hideHeader?: boolean;
  activeLessonContext?: LessonContext | null;
  onLessonRequest?: (topic: string) => void;
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
const LESSON_REQUEST_RE = /\b(?:build|make|create|generate|start|give me)\s+(?:an?\s+)?(?:[\w-]+\s+){0,4}lesson\b|\b(?:i(?:'d| would) like|i want|i need)\s+(?:an?\s+)?(?:[\w-]+\s+){0,4}lesson\b|\bteach me\b|\bi want to learn about\b|\bdeep dive (?:into|on)\b|\bexplain .+ in depth\b/i;

function inferLessonTrack(text: string): Track {
  const normalized = text.toLowerCase();
  if (/bible|scripture|yahweh|yeshua|faith|disciple|proverb/.test(normalized)) return "DISCIPLESHIP";
  if (/history|war|ancient|civilization|primary source/.test(normalized)) return "TRUTH_HISTORY";
  if (/government|constitution|econom|money|business|market/.test(normalized)) return "GOVERNMENT_ECONOMICS";
  if (/justice|rights|prison|reform|activis/.test(normalized)) return "JUSTICE_CHANGEMAKING";
  if (/garden|farm|soil|seed|animal|homestead|cook|food/.test(normalized)) return "HOMESTEADING";
  if (/health|body|nutrition|herb|medicine/.test(normalized)) return "HEALTH_NATUROPATHY";
  if (/math|algebra|geometry|fraction|equation|number/.test(normalized)) return "APPLIED_MATHEMATICS";
  if (/write|poem|novel|book|literature|grammar|language/.test(normalized)) return "ENGLISH_LITERATURE";
  if (/art|design|music|film|creative|commission/.test(normalized)) return "CREATIVE_ECONOMY";
  return "CREATION_SCIENCE";
}

function suggestionMatchScore(text: string, title: string, description: string): number {
  const requestWords = new Set(
    text.toLowerCase().match(/[a-z]{3,}/g)?.filter((word) => !["lesson", "like", "want", "need", "give", "make"].includes(word)) ?? [],
  );
  const candidate = `${title} ${description}`.toLowerCase();
  return [...requestWords].reduce((score, word) => score + (candidate.includes(word) ? 1 : 0), 0);
}

/** Extract an optional duration when the student happens to mention one. */
function parseMinutes(text: string): number | undefined {
  const hoursMatch = text.match(/(\d+(?:\.\d+)?)\s*hour/i);
  const minutesMatch = text.match(/(\d+)\s*min/i);
  const anHourMatch = /\ban hour\b/i.test(text);
  const halfHourMatch = /half.{0,5}hour/i.test(text);

  let total = 0;
  if (hoursMatch) total += parseFloat(hoursMatch[1]) * 60;
  if (minutesMatch) total += parseInt(minutesMatch[1]);
  if (anHourMatch && !hoursMatch) total += 60;
  if (halfHourMatch && !minutesMatch) total += 30;
  return total > 0 ? Math.round(total) : undefined;
}

// ── Activity credit receipt ────────────────────────────────────────────────────

function ActivityCreditCard({ result }: { result: ActivityReportResponse }) {
  const [uploading, setUploading] = useState(false);
  const [evidenceUrl, setEvidenceUrl] = useState<string | null>(result.evidence_urls?.[0] ?? null);
  const [uploadError, setUploadError] = useState("");

  async function attachEvidence(file: File | undefined) {
    if (!file) return;
    setUploading(true);
    setUploadError("");
    try {
      const uploaded = await uploadActivityEvidence(result.activity_id, file);
      setEvidenceUrl(uploaded.file_url);
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : "Photo upload failed");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="space-y-2 pt-1">
      <div
        className="rounded-xl p-3 space-y-2"
        style={{ background: "#F0FDF4", border: "1.5px solid #2F4731" }}
      >
        <p className="text-xs font-bold text-[#2F4731] uppercase tracking-wider">
          Learning recorded
        </p>
        <p className="text-sm font-bold text-[#2F4731]">{result.course_title}</p>
        <p className="text-xs text-[#2F4731]/70">{result.activity_description}</p>
        <div className="flex flex-wrap gap-2 pt-1 border-t border-[#2F4731]/20">
          <span className="text-xs font-bold text-[#BD6809]">
            {result.credit_hours > 0
              ? `${result.credit_hours} credit hr${result.credit_hours !== 1 ? "s" : ""}`
              : "Learning evidence saved"}
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
        <div className="pt-2">
          {evidenceUrl ? (
            <p className="text-xs font-bold text-[#166534]">✓ Photo evidence attached to your portfolio</p>
          ) : (
            <label className="inline-flex cursor-pointer items-center rounded-lg bg-[#2F4731] px-3 py-2 text-xs font-bold text-white">
              {uploading ? "Adding photo…" : "Add a project photo"}
              <input type="file" accept="image/*,video/mp4,video/webm,video/quicktime" className="sr-only" disabled={uploading} onChange={(event) => void attachEvidence(event.target.files?.[0])} />
            </label>
          )}
          {uploadError && <p className="mt-1 text-xs text-red-700">{uploadError}</p>}
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
  hideHeader = false,
  activeLessonContext,
  onLessonRequest,
  highlightedContext,
  onHighlightedContextUsed,
}: AdelineChatPanelProps) {
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([WELCOME_MSG]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [conversationHistory, setConversationHistory] = useState<ConversationMessage[]>([]);
  const [pendingHighlight, setPendingHighlight] = useState<string | null>(null);
  const [activeLessonId, setActiveLessonId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // ── ALU Stream: progressive rendering + ALU playlist + temporal friction ─
  const {
    components: streamingComponents,
    componentOrder: streamingComponentOrder,
    remediations,
    statusMessage: streamStatus,
    triggerRemediation,
  } = useALUStream({ studentId, lessonId: activeLessonId ?? undefined });

  // Handler for student interaction events from streaming GenUI components.
  // This implements the bidirectional remediation loop: when a student
  // struggles, the event is piped to the backend which streams back a
  // remedial component on the same conceptual connection.
  const handleStreamingComponentEvent = useCallback(
    async (params: {
      componentId: string;
      componentType: string;
      event: string;
      state: Record<string, unknown>;
    }) => {
      // Fire-and-forget telemetry for all events
      try {
        const { fireGenUICallback } = await import("@/lib/genui-callback");
        await fireGenUICallback({
          studentId,
          lessonId: activeLessonId ?? "",
          componentType: params.componentType,
          event: params.event,
          state: params.state,
          blockId: params.componentId,
        });
      } catch {
        // Non-blocking telemetry
      }

      // Trigger bidirectional remediation for struggle events
      const isStruggle =
        params.event === "onStruggle" ||
        params.event === "onWrongAnswer" ||
        (params.event === "onHint" &&
          (params.state.hintsUsed as number) >= 3);

      if (isStruggle) {
        await triggerRemediation({
          sourceComponentId: params.componentId,
          componentType: params.componentType,
          event: params.event,
          studentState: params.state,
        });
      }
    },
    [studentId, activeLessonId, triggerRemediation],
  );

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
      } else if (LESSON_REQUEST_RE.test(text)) {
        const track = inferLessonTrack(text);
        const plan = await getLearningPlan(studentId, 10);
        const plannedTask = plan.suggestions
          .filter((suggestion) => suggestion.track === track)
          .sort((left, right) =>
            suggestionMatchScore(text, right.title, right.description) -
            suggestionMatchScore(text, left.title, left.description)
          )[0];
        if (!plannedTask) {
          addMessage({
            role: "adeline",
            content: "I don’t have a matching assignment in your learning plan yet. Tell me a little more about what you want to learn, and I’ll shape the right next step before building it.",
          });
          return;
        }
        addMessage({
          role: "adeline",
          content: `I found the right assignment in your learning plan: “${plannedTask.title}.” I’m opening the full family lesson now.`,
        });
        onLessonRequest?.(plannedTask.title);
        router.push(`/dashboard/lesson/${encodeURIComponent(plannedTask.id)}`);
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
        // Life-to-learning: recognize educational value immediately. Duration is
        // optional metadata, never a gate before discussing what was learned.
        const minutes = parseMinutes(text);
        const result = await reportActivity(
          {
            student_id: studentId,
            grade_level: gradeLevel,
            description: text,
            ...(minutes ? { time_minutes: minutes } : {}),
          },
          "STUDENT",
        );
        addMessage({ role: "adeline", content: `${result.adeline_note} If you have a photo, add it below as portfolio evidence.`, rich: { type: "activityCredit", result } });
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
                ? { ...m, content: "I ran into a hiccup — give me a moment and try again.", streaming: false }
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
        content: "I ran into a hiccup — give me a moment and try again.",
      });
    } finally {
      setIsLoading(false);
    }
  }, [input, isLoading, activeLessonContext, studentId, gradeLevel, onLessonRequest, addMessage, conversationHistory, router]);

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
      {!hideHeader && (
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
      )}

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

        {/* Streaming GenUI components — progressive rendering */}
        {streamingComponentOrder.length > 0 && (
          <div className="w-full">
            {streamStatus && (
              <div className="flex items-center gap-2 mb-3 px-2">
                <Loader2 size={12} className="animate-spin text-[#BD6809]" />
                <span className="text-xs text-[#2F4731]/60 italic">
                  {streamStatus}
                </span>
              </div>
            )}
            <StreamingGenUIRenderer
              components={streamingComponents}
              componentOrder={streamingComponentOrder}
              remediations={remediations}
              onComponentEvent={handleStreamingComponentEvent}
            />
          </div>
        )}

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
