"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Sparkles, Send, Loader2 } from "lucide-react";
import { scaffold, listProjects, getProject, reportActivity, streamConversation, uploadActivityEvidence } from "@/lib/brain-client";
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
          {result.sealed ? "Learning recorded" : "Learning explored"}
        </p>
        <p className="text-sm font-bold text-[#2F4731]">{result.course_title}</p>
        <p className="text-xs text-[#2F4731]/70">{result.activity_description}</p>
        <div className="flex flex-wrap gap-2 pt-1 border-t border-[#2F4731]/20">
          <span className="text-xs font-bold text-[#BD6809]">
            {!result.sealed
              ? "Tell Adeline what you learned"
              : result.credit_hours > 0
              ? `${result.credit_hours} competency credit`
              : "Concept evidence saved"}
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
          {!result.sealed ? (
            <p className="text-xs font-bold text-[#92400E]">The reflection is safe here; the permanent record can be retried later.</p>
          ) : evidenceUrl ? (
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
  RESOURCE_COLLECTION: { icon: "🎮", bg: "#F0FDF4", border: "#2F4731", color: "#2F4731", label: "Choose an experience" },
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

function ConversationBlockCard({ block, onReflect }: { block: Record<string, unknown>; onReflect?: (prompt: string) => void }) {
  const [sharedResource, setSharedResource] = useState<string | null>(null);
  const blockType = (block.block_type as string) ?? "NARRATIVE";
  const c = BLOCK_CONFIGS[blockType] ?? BLOCK_CONFIGS.NARRATIVE;
  const title   = block.title   as string | undefined;
  const content = block.content as string | undefined;
  const metadata = block.metadata as { resources?: Array<Record<string, unknown>> } | undefined;
  const resources = metadata?.resources ?? [];

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
      {blockType === "RESOURCE_COLLECTION" && resources.length > 0 && (
        <div className="space-y-2 pt-2">
          {resources.map((resource, index) => {
            const url = (resource.editor_url || resource.embed_url || resource.source_url) as string | undefined;
            const title = (resource.title as string) || `Resource ${index + 1}`;
            const resourceId = (resource.id as string) || `${title}-${index}`;
            async function shareWithFamily() {
              if (!url) return;
              const response = await fetch('/brain/family/feed', {
                method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ kind: 'GAME', title, body: `Would anyone like to try this with me? ${String(resource.mastery_prompt || '')}`.trim(), resource_url: url }),
              });
              if (response.ok) setSharedResource(resourceId);
            }
            return (
              <div key={resourceId} className="rounded-lg border border-[#2F4731]/15 bg-white p-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-bold text-[#2F4731]">{title}</p>
                    <p className="mt-0.5 text-[11px] font-semibold uppercase tracking-wide text-[#BD6809]">{String(resource.provider || '')} · {String(resource.resource_type || '').replaceAll('_', ' ')}</p>
                  </div>
                  {url && <a href={url} target="_blank" rel="noopener noreferrer" className="shrink-0 rounded-lg bg-[#2F4731] px-3 py-2 text-xs font-bold text-white no-underline">Open</a>}
                </div>
                {resource.description && <p className="mt-2 text-xs leading-5 text-[#2F4731]/70">{String(resource.description)}</p>}
                {resource.mastery_prompt && onReflect && (
                  <div className="mt-2 flex flex-wrap gap-3">
                    <button type="button" onClick={() => onReflect(`I worked with ${title}. Here is what I built, tested, decided, or learned: `)} className="text-xs font-bold text-[#2F4731] underline underline-offset-4">I finished—talk with Adeline</button>
                    {url && <button type="button" onClick={() => void shareWithFamily()} className="text-xs font-bold text-[#BD6809] underline underline-offset-4">{sharedResource === resourceId ? 'Shared with family' : 'Invite my family'}</button>}
                  </div>
                )}
              </div>
            );
          })}
          <p className="text-[11px] text-[#2F4731]/60">Credit comes from what you can demonstrate or explain afterward—not from opening the link or time spent.</p>
        </div>
      )}
    </div>
  );
}

// ── AdelineChatPanel ───────────────────────────────────────────────────────────

export function AdelineChatPanel({
  studentId,
  gradeLevel,
  hideHeader = false,
  activeLessonContext,
  highlightedContext,
  onHighlightedContextUsed,
}: AdelineChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([WELCOME_MSG]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [conversationHistory, setConversationHistory] = useState<ConversationMessage[]>([]);
  const [pendingActivity, setPendingActivity] = useState<string | null>(null);
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
      } else if (PROJECT_LIST_RE.test(text)) {
        // Project catalog intent
        addMessage({ role: "adeline", content: "Let me pull up the project catalog for you…" });
        const { projects } = await listProjects({}, "STUDENT");
        addMessage({
          role: "adeline",
          content: "",
          rich: { type: "projectList", projects },
        });
      } else if (pendingActivity || ACTIVITY_RE.test(text)) {
        // Life-to-learning: recognize educational value immediately. Duration is
        // irrelevant to credit; follow-up answers can demonstrate the concepts.
        try {
          const result = await reportActivity(
            {
              student_id: studentId,
              grade_level: gradeLevel,
              description: pendingActivity
                ? `Activity: ${pendingActivity}\nLearner's explanation of what they understand: ${text}`
                : text,
            },
            "STUDENT",
          );
          setPendingActivity(result.sealed ? null : (pendingActivity || text));
          addMessage({ role: "adeline", content: `${result.adeline_note}${result.sealed ? " If you have a photo, add it below as portfolio evidence." : ""}`, rich: { type: "activityCredit", result } });
        } catch {
          addMessage({
            role: "adeline",
            content: "That is real learning. Think about what you noticed, what decisions you made, what changed from start to finish, and what you would try next. I could not save the permanent learning record just now, but we can keep exploring it here.",
          });
        }
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
                ? { ...m, content: "I could not reach the conversation service just now. Your message is still here—please try once more.", streaming: false }
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
        content: "I could not reach the service just now. Your message is still here—please try once more.",
      });
    } finally {
      setIsLoading(false);
    }
  }, [input, isLoading, activeLessonContext, studentId, gradeLevel, addMessage, conversationHistory]);

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
                        <ConversationBlockCard key={i} block={seg.data} onReflect={(prompt) => { setInput(prompt); inputRef.current?.focus(); }} />
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
