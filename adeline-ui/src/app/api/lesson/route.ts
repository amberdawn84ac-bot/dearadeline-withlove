/**
 * POST /api/lesson
 *
 * Next.js → FastAPI SSE translation bridge for SDK v3.
 *
 * Receives a POST from useChat({ transport: new DefaultChatTransport({ api: '/api/lesson' }) }),
 * calls FastAPI POST /brain/lesson/stream, and translates the SSE events into the
 * Vercel AI SDK v3 UI Message Stream format.
 *
 * SDK v3 expects JSON SSE events (not the old text-based protocol):
 *   data: {"type": "text-start", "id": "..."}
 *   data: {"type": "text-delta", "text": "..."}
 *   data: {"type": "data", "data": {...}}        — data annotations
 *   data: {"type": "tool-input-start", ...}       — tool calls
 *   data: {"type": "finish-step"}                 — step completion
 */

import { NextRequest } from "next/server";

const BRAIN_URL =
  process.env.NEXT_PUBLIC_BRAIN_URL ?? "http://localhost:8000";

export const runtime = "nodejs";
export const maxDuration = 120;

export async function POST(req: NextRequest) {
  const authHeader = req.headers.get("authorization") ?? "";
  const body = await req.json();

  // useChat sends { messages: [...] }. The last user message contains our request payload.
  // We pass the raw body through as lesson_request fields.
  const lessonRequest = body.lesson_request ?? body;

  let upstream: Response;
  try {
    upstream = await fetch(`${BRAIN_URL}/brain/lesson/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(authHeader ? { Authorization: authHeader } : {}),
      },
      body: JSON.stringify(lessonRequest),
    });
  } catch (err) {
    return new Response(
      `2:[{"type":"error","message":"Cannot reach adeline-brain: ${err}"}]\n` +
      `d:{"finishReason":"error"}\n`,
      {
        status: 200,
        headers: {
          "Content-Type": "text/plain; charset=utf-8",
          "x-vercel-ai-data-stream": "v1",
        },
      }
    );
  }

  if (!upstream.ok || !upstream.body) {
    const detail = await upstream.text().catch(() => "");
    const errorEvent = JSON.stringify({ type: "error", message: `Backend error ${upstream.status}: ${detail}` });
    return new Response(
      `data: ${errorEvent}\n\n`,
      {
        status: 200,
        headers: {
          "Content-Type": "text/event-stream",
          "Cache-Control": "no-cache",
          "X-Accel-Buffering": "no",
        },
      }
    );
  }

  // Stream-transform: FastAPI SSE → SDK v3 UI Message Stream (JSON SSE format)
  const encoder = new TextEncoder();
  const decoder = new TextDecoder();

  const readable = new ReadableStream({
    async start(controller) {
      const reader = upstream.body!.getReader();
      let buffer = "";

      const enqueue = (event: Record<string, unknown>) => {
        const line = `data: ${JSON.stringify(event)}\n\n`;
        controller.enqueue(encoder.encode(line));
      };

      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          for (const raw of lines) {
            const line = raw.trim();
            if (!line.startsWith("data:")) continue;

            let event: Record<string, unknown>;
            try {
              event = JSON.parse(line.slice(5).trim());
            } catch {
              continue;
            }

            switch (event.type) {
              case "status":
                // Data annotation for status updates
                enqueue({ type: "data", data: { type: "status", message: event.message } });
                break;

              case "block":
                // Data annotation for blocks
                enqueue({ type: "data", data: { type: "block", block: event.block } });
                break;

              case "tool_call": {
                const toolCallId = crypto.randomUUID();
                // Tool call start
                enqueue({
                  type: "tool-input-start",
                  toolCallId,
                  toolName: event.name,
                });
                // Tool input (args)
                enqueue({
                  type: "tool-input-delta",
                  toolCallId,
                  input: JSON.stringify(event.props),
                });
                // Tool call complete
                enqueue({
                  type: "tool-input-finish",
                  toolCallId,
                });
                // Tool result (immediately resolve)
                enqueue({
                  type: "tool-result",
                  toolCallId,
                  result: event.props,
                });
                break;
              }

              case "done":
                // Data annotation for done event
                enqueue({ type: "data", data: { type: "done", ...event } });
                // Finish the step
                enqueue({ type: "finish-step" });
                break;

              case "error":
                // Data annotation for error
                enqueue({ type: "data", data: { type: "error", message: event.message } });
                enqueue({ type: "finish-step" });
                break;
            }
          }
        }
      } catch (err) {
        enqueue({ type: "data", data: { type: "error", message: String(err) } });
        enqueue({ type: "finish-step" });
      } finally {
        controller.close();
      }
    },
  });

  return new Response(readable, {
    status: 200,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      "X-Accel-Buffering": "no",
    },
  });
}
