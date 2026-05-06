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
 *   9:{"toolCallId":"..."}\n — tool call
 *   a:{"toolCallId":"..."}\n — tool result
 *   d:{"finishReason":"stop"}\n — finish marker
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
                // 2: — data annotation
                enqueue(
                  `2:[${JSON.stringify({ type: "status", message: event.message })}]\n`
                );
                break;

              case "block":
                // 2: — data annotation for blocks
                enqueue(
                  `2:[${JSON.stringify({ type: "block", block: event.block })}]\n`
                );
                break;

              case "tool_call": {
                const toolCallId = crypto.randomUUID();
                // 9: — tool call part
                enqueue(
                  `9:${JSON.stringify({
                    toolCallId,
                    toolName: event.name,
                    args: event.props,
                  })}\n`
                );
                // a: — tool result (immediately resolve so toolInvocation.state === "result")
                enqueue(
                  `a:${JSON.stringify({
                    toolCallId,
                    result: event.props,
                  })}\n`
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
