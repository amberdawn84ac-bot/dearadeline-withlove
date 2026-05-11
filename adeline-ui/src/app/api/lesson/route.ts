/**
 * POST /api/lesson
 *
 * Next.js → FastAPI SSE translation bridge.
 *
 * Translates FastAPI SSE events into the ai@6 UI Message Stream format
 * (newline-delimited JSON objects) consumed by DefaultChatTransport.
 *
 * Chunk types emitted:
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
 */

import { NextRequest } from "next/server";

const BRAIN_URL = (
  process.env.NEXT_PUBLIC_BRAIN_URL ||
  process.env.BRAIN_INTERNAL_URL ||
  "http://localhost:8000"
).replace(/\/$/, "");

export const dynamic = "force-dynamic";
export const runtime = "nodejs";
export const maxDuration = 120;

function chunk(obj: unknown): string {
  return JSON.stringify(obj) + "\n";
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
          "Content-Type": "application/x-ndjson",
          "x-vercel-ai-ui-message-stream": "v1",
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
          "Content-Type": "application/x-ndjson",
          "x-vercel-ai-ui-message-stream": "v1",
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
          "Content-Type": "application/x-ndjson",
          "x-vercel-ai-ui-message-stream": "v1",
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
      };

      // Signal stream start
      enqueue(chunk({ type: "start" }));

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
                const msg = String(event.message ?? "");
                ensureTextStarted();
                enqueue(chunk({ type: "text-delta", id: "t0", delta: msg }));
                enqueue(chunk({ type: "data-status", data: { message: msg } }));
                break;
              }

              case "block": {
                const blockContent = (event.block as Record<string, unknown>)?.content as string | undefined;
                if (blockContent) {
                  ensureTextStarted();
                  enqueue(chunk({ type: "text-delta", id: "t0", delta: blockContent + "\n\n" }));
                }
                enqueue(chunk({ type: "data-block", data: { block: event.block } }));
                break;
              }

              case "tool_call": {
                const toolCallId = crypto.randomUUID();
                enqueue(chunk({
                  type: "tool-input-available",
                  toolCallId,
                  toolName: String(event.name ?? "unknown"),
                  input: event.props,
                  dynamic: true,
                }));
                enqueue(chunk({
                  type: "tool-output-available",
                  toolCallId,
                  output: event.props,
                }));
                break;
              }

              case "done": {
                enqueue(chunk({ type: "data-done", data: { title: event.title } }));
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
      "Content-Type": "application/x-ndjson",
      "x-vercel-ai-ui-message-stream": "v1",
      "Cache-Control": "no-cache",
      "X-Accel-Buffering": "no",
    },
  });
}
