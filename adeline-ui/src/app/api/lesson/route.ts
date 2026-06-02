/**
 * POST /api/lesson
 *
 * Next.js → FastAPI SSE translation bridge.
 *
 * Translates FastAPI SSE events into BOTH:
 *   1. The ai@6 UI Message Stream format (for backward compatibility)
 *   2. The Vercel AI SDK Data Stream Protocol with 2: annotations
 *      for GenUI progressive rendering and bidirectional remediation.
 *
 * UI Message Stream chunks (existing):
 *   {"type":"start"}
 *   {"type":"text-start","id":"t0"}
 *   {"type":"text-delta","id":"t0","delta":"..."}
 *   {"type":"text-end","id":"t0"}
 *   {"type":"data-status","data":{"message":"..."}}
 *   {"type":"data-block","data":{"block":{...}}}
 *   {"type":"data-done","data":{"title":"..."}}
 *   {"type":"data-error","data":{"message":"..."}}
 *   {"type":"tool-input-available","toolCallId":"...","toolName":"...","input":{...},"dynamic":true}
 *   {"type":"tool-output-available","toolCallId":"...","output":{...}}
 *   {"type":"finish","finishReason":"stop"}
 *
 * Data Stream Protocol lines (new — for useGenUIStream):
 *   2:[{"type":"genui_skeleton",...}]   → Component placeholder
 *   2:[{"type":"genui_complete",...}]   → Full component props
 *   2:[{"type":"remediation",...}]      → Remediation component injection
 *   2:[{"type":"status",...}]           → Progress status
 *   c:{"toolCallId":"...","toolName":"student_needs_remediation",...}
 */

import { NextRequest } from "next/server";
import { logger } from "@/lib/logger";

const BRAIN_URL = (
  process.env.BRAIN_INTERNAL_URL ||
  process.env.BRAIN_URL ||
  process.env.NEXT_PUBLIC_BRAIN_URL ||
  "https://dearadeline-withlove-production.up.railway.app"
).replace(/\/$/,  "");

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
export const maxDuration = 120;

function chunk(obj: unknown): string {
  return `data: ${JSON.stringify(obj)}\n\n`;
}

/** Encode a Data Stream Protocol annotation (2: line). */
function dataAnnotation(payload: Record<string, unknown>): string {
  return `2:${JSON.stringify([payload])}\n`;
}

/** Encode a Data Stream Protocol tool-call (c: line). */
function dataToolCall(
  toolCallId: string,
  toolName: string,
  args: Record<string, unknown>,
): string {
  return `c:${JSON.stringify({ toolCallId, toolName, args })}\n`;
}

/** Encode a Data Stream Protocol finish (d: line). */
function dataFinish(reason: string): string {
  return `d:${JSON.stringify({ finishReason: reason })}\n`;
}

export async function POST(req: NextRequest) {
  const body = await req.json();
  const lessonRequest = body.lesson_request ?? body;

  const resolvedAuth = req.headers.get("authorization") ?? "";
  if (!resolvedAuth) {
    return new Response(
      chunk({ type: "data-error", data: { message: "Missing Authorization header — please log in again" } }) +
      chunk({ type: "finish", finishReason: "error" }),
      {
        status: 200,
        headers: {
          "Content-Type": "text/event-stream",
          "x-vercel-ai-ui-message-stream": "v1",
          "x-vercel-ai-data-stream": "v1",
        },
      }
    );
  }

  let upstream: Response;
  try {
    upstream = await fetch(`${BRAIN_URL}/lesson/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: resolvedAuth,
      },
      body: JSON.stringify(lessonRequest),
    });
  } catch (err) {
    return new Response(
      chunk({ type: "data-error", data: { message: `Cannot reach adeline-brain: ${err}` } }) +
      chunk({ type: "finish", finishReason: "error" }),
      {
        status: 200,
        headers: {
          "Content-Type": "text/event-stream",
          "x-vercel-ai-ui-message-stream": "v1",
          "x-vercel-ai-data-stream": "v1",
        },
      }
    );
  }

  if (!upstream.ok || !upstream.body) {
    const detail = await upstream.text().catch(() => "");
    return new Response(
      chunk({ type: "data-error", data: { message: `Backend error ${upstream.status}: ${detail}` } }) +
      chunk({ type: "finish", finishReason: "error" }),
      {
        status: 200,
        headers: {
          "Content-Type": "text/event-stream",
          "x-vercel-ai-ui-message-stream": "v1",
          "x-vercel-ai-data-stream": "v1",
        },
      }
    );
  }

  const encoder = new TextEncoder();
  const decoder = new TextDecoder();

  const readable = new ReadableStream({
    async start(controller) {
      const reader = upstream.body!.getReader();
      let buffer = "";
      let textStarted = false;
      let finished = false;

      const enqueue = (line: string) =>
        controller.enqueue(encoder.encode(line));

      const ensureTextStarted = () => {
        if (!textStarted) {
          enqueue(chunk({ type: "text-start", id: "t0" }));
          textStarted = true;
        }
      };

      const closeStream = (finishReason: string) => {
        if (finished) return;
        finished = true;
        if (textStarted) enqueue(chunk({ type: "text-end", id: "t0" }));
        enqueue(chunk({ type: "finish", finishReason }));
        // Also emit Data Stream Protocol finish
        enqueue(dataFinish(finishReason));
        enqueue("data: [DONE]\n\n");
      };

      // Signal stream start
      enqueue(chunk({ type: "start" }));

      let firstChunk = true;

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const frames = buffer.split("\n\n");
          buffer = frames.pop() ?? "";

          for (const frame of frames) {
            const line = frame.split("\n").find((l) => l.trimStart().startsWith("data:")) ?? "";
            if (!line) continue;

            let event: Record<string, unknown>;
            try {
              event = JSON.parse(line.slice(5).trim());
            } catch {
              continue;
            }

            if (firstChunk) {
              logger.debug("[lesson/route] First SSE event from brain:", JSON.stringify(event).slice(0, 200));
              firstChunk = false;
            }

            switch (event.type) {
              case "status": {
                const msg = String(event.message ?? "");
                ensureTextStarted();
                enqueue(chunk({ type: "text-delta", id: "t0", delta: msg }));
                enqueue(chunk({ type: "data-status", data: { message: msg } }));
                // Data Stream Protocol: status annotation
                enqueue(dataAnnotation({ type: "status", message: msg }));
                break;
              }

              case "block": {
                const blockContent = (event.block as Record<string, unknown>)?.content as string | undefined;
                if (blockContent) {
                  ensureTextStarted();
                  enqueue(chunk({ type: "text-delta", id: "t0", delta: blockContent + "\n\n" }));
                }
                // UI Message Stream format (backward compat)
                enqueue(chunk({ type: "data-block", data: { block: event.block } }));
                // Data Stream Protocol 2: annotation — ai@6 useChat reads these, not the data: lines
                enqueue(dataAnnotation({ type: "data-block", data: { block: event.block } }));
                break;
              }

              // ── GenUI Progressive Rendering events ─────────────────
              // These are emitted by the brain's lesson_stream.py and
              // translated into 2: Data Stream Protocol annotations.

              case "genui_skeleton": {
                enqueue(dataAnnotation({
                  type: "genui_skeleton",
                  componentId: String(event.componentId ?? ""),
                  componentType: String(event.componentType ?? ""),
                  props: null,
                  state: "skeleton",
                  hints: event.hints ?? {},
                  lessonId: event.lessonId ?? "",
                  track: event.track ?? "",
                }));
                break;
              }

              case "genui_complete": {
                enqueue(dataAnnotation({
                  type: "genui_complete",
                  componentId: String(event.componentId ?? ""),
                  componentType: String(event.componentType ?? ""),
                  props: event.props ?? {},
                  state: "complete",
                  callbacks: event.callbacks ?? [],
                  initialState: event.initialState ?? {},
                  lessonId: event.lessonId ?? "",
                  track: event.track ?? "",
                }));
                break;
              }

              case "genui_props": {
                enqueue(dataAnnotation({
                  type: "genui_props",
                  componentId: String(event.componentId ?? ""),
                  props: event.props ?? {},
                  state: String(event.state ?? "partial"),
                }));
                break;
              }

              case "tool_call": {
                const toolCallId = (event.props as Record<string, unknown>)?.toolCallId as string
                  ?? crypto.randomUUID();
                const toolName = String(event.name ?? "unknown");

                // UI Message Stream format (backward compat)
                enqueue(chunk({
                  type: "tool-input-available",
                  toolCallId,
                  toolName,
                  input: event.props,
                  dynamic: true,
                }));
                enqueue(chunk({
                  type: "tool-output-available",
                  toolCallId,
                  output: event.props,
                }));

                // Data Stream Protocol: tool-call (c: line)
                enqueue(dataToolCall(
                  toolCallId,
                  toolName,
                  (event.props ?? {}) as Record<string, unknown>,
                ));
                break;
              }

              case "done": {
                enqueue(chunk({ type: "data-done", data: { title: event.title } }));
                // Data Stream Protocol: done annotation
                enqueue(dataAnnotation({
                  type: "data-done",
                  data: {
                    title: event.title ?? "",
                    lesson_id: event.lesson_id ?? "",
                    agent_name: event.agent_name ?? "",
                    oas_standards: event.oas_standards ?? [],
                  },
                }));
                closeStream("stop");
                break;
              }

              case "error": {
                enqueue(chunk({ type: "data-error", data: { message: String(event.message ?? "") } }));
                closeStream("error");
                break;
              }
            }
          }
        }
      } catch (err) {
        enqueue(chunk({ type: "data-error", data: { message: String(err) } }));
        closeStream("error");
      } finally {
        reader.releaseLock();
        closeStream("stop");
        controller.close();
      }
    },
  });

  return new Response(readable, {
    status: 200,
    headers: {
      "Content-Type": "text/event-stream",
      "x-vercel-ai-ui-message-stream": "v1",
      "x-vercel-ai-data-stream": "v1",
      "Cache-Control": "no-cache",
      "X-Accel-Buffering": "no",
    },
  });
}
