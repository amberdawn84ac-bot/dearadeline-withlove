/**
 * POST /api/lesson
 *
 * Next.js → FastAPI SSE translation bridge.
 *
 * Receives a POST from useChat({ transport: new DefaultChatTransport({ api: '/api/lesson' }) }),
 * calls FastAPI POST /brain/lesson/stream, and translates the SSE events into the
 * Vercel AI SDK Data Stream Protocol.
 *
 * Data Stream Protocol format:
 *   0:"text chunk"\n        — text content
 *   2:[{"key":"value"}]\n    — data annotation (arbitrary JSON array)
 *   9:[{"toolCallId":"..."}]\n — tool call  (SDK v3: must be a JSON array)
 *   a:[{"toolCallId":"..."}]\n — tool result (SDK v3: must be a JSON array)
 *   d:{"finishReason":"stop"}\n — finish marker
 */

import { NextRequest } from "next/server";
import { createServerClient } from "@supabase/ssr";

const BRAIN_URL = (
  process.env.NEXT_PUBLIC_BRAIN_URL ||
  process.env.BRAIN_INTERNAL_URL ||
  "http://localhost:8000"
).replace(/\/$/, "");

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
export const maxDuration = 120;

export async function POST(req: NextRequest) {
  const body = await req.json();

  // useChat sends { messages: [...] }. The last user message contains our request payload.
  // We pass the raw body through as lesson_request fields.
  const lessonRequest = body.lesson_request ?? body;

  // Read the Supabase JWT from the HttpOnly cookie (set by Supabase Auth on login).
  // Falls back to the Authorization header if present (e.g., direct API calls).
  let resolvedAuth = req.headers.get("authorization") ?? "";
  if (!resolvedAuth) {
    const supabase = createServerClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://dummy.supabase.co',
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'dummy-anon-key',
      {
        cookies: {
          getAll: () => req.cookies.getAll(),
          setAll: () => {},
        },
      },
    );
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    if (token) resolvedAuth = `Bearer ${token}`;
  }

  let upstream: Response;
  try {
    upstream = await fetch(`${BRAIN_URL}/lesson/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(resolvedAuth ? { Authorization: resolvedAuth } : {}),
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
    return new Response(
      `2:[{"type":"error","message":"Backend error ${upstream.status}: ${detail}"}]\n` +
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

  // Stream-transform: FastAPI SSE → Vercel AI SDK Data Stream Protocol
  const encoder = new TextEncoder();
  const decoder = new TextDecoder();

  const readable = new ReadableStream({
    async start(controller) {
      const reader = upstream.body!.getReader();
      let buffer = "";

      const enqueue = (line: string) =>
        controller.enqueue(encoder.encode(line));

      let firstChunk = true;

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

            if (firstChunk) {
              console.log("[lesson/route] First SSE event from brain:", JSON.stringify(event).slice(0, 200));
              firstChunk = false;
            }

            switch (event.type) {
              case "status": {
                const statusMsg = String(event.message ?? "");
                // 0: — text chunk so useChat registers content and activates
                enqueue(`0:${JSON.stringify(statusMsg)}\n`);
                // 2: — data annotation for UI status display
                enqueue(
                  `2:[${JSON.stringify({ type: "status", message: statusMsg })}]\n`
                );
                break;
              }

              case "block": {
                const blockContent = (event.block as Record<string, unknown>)?.content as string | undefined;
                // 0: — text chunk: emit the block's text content so useChat stays active
                if (blockContent) {
                  enqueue(`0:${JSON.stringify(blockContent + "\n\n")}\n`);
                }
                // 2: — data annotation carries the full structured block
                enqueue(
                  `2:[${JSON.stringify({ type: "block", block: event.block })}]\n`
                );
                break;
              }

              case "tool_call": {
                const toolCallId = crypto.randomUUID();
                // 9: — tool call part (SDK v3 requires a JSON ARRAY)
                enqueue(
                  `9:[${JSON.stringify({
                    toolCallId,
                    toolName: event.name,
                    args: event.props,
                  })}]\n`
                );
                // a: — tool result array (immediately resolve so toolInvocation.state === "result")
                enqueue(
                  `a:[${JSON.stringify({
                    toolCallId,
                    result: event.props,
                  })}]\n`
                );
                break;
              }

              case "done":
                // 2: — data annotation for done event
                enqueue(
                  `2:[${JSON.stringify({ type: "done", ...event })}]\n`
                );
                // d: — finish marker
                enqueue(`d:${JSON.stringify({ finishReason: "stop" })}\n`);
                break;

              case "error":
                enqueue(
                  `2:[${JSON.stringify({ type: "error", message: event.message })}]\n`
                );
                enqueue(`d:${JSON.stringify({ finishReason: "error" })}\n`);
                break;
            }
          }
        }
      } catch (err) {
        enqueue(
          `2:[${JSON.stringify({ type: "error", message: String(err) })}]\n`
        );
        enqueue(`d:${JSON.stringify({ finishReason: "error" })}\n`);
      } finally {
        reader.releaseLock();
        controller.close();
      }
    },
  });

  return new Response(readable, {
    status: 200,
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "x-vercel-ai-data-stream": "v1",
      "Cache-Control": "no-cache",
      "X-Accel-Buffering": "no",
    },
  });
}
