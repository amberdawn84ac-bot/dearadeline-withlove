/**
 * POST /api/reader-chat
 *
 * Next.js → FastAPI SSE translation bridge for Reader Chat.
 *
 * Receives a POST from useChat({ api: '/api/reader-chat' }), calls FastAPI
 * POST /brain/conversation/stream, and translates the SSE events into the
 * Vercel AI SDK Data Stream Protocol so useChat can consume it natively.
 *
 * Vercel AI SDK Data Stream Protocol prefixes:
 *   0:"<text>"   — text delta (rendered as assistant message content)
 *   2:[...]      — data annotation (arbitrary JSON array, attached to message)
 *   d:{...}      — finish/done marker
 *
 * FastAPI SSE events are translated to text deltas for the reader chat.
 */

import { NextRequest } from "next/server";

const BRAIN_URL = (
  process.env.BRAIN_INTERNAL_URL ||
  process.env.BRAIN_URL ||
  process.env.NEXT_PUBLIC_BRAIN_URL ||
  "https://dearadeline-withlove-production.up.railway.app"
).replace(/\/$/, "");

export const runtime = "nodejs";
export const maxDuration = 120;

export async function POST(req: NextRequest) {
  const authHeader = req.headers.get("authorization") ?? "";
  const body = await req.json();

  // Extract context from the request body
  const { messages, context } = body;
  
  // Get the last user message content
  const lastMessage = messages?.[messages.length - 1];
  const userContent = lastMessage?.parts
    ?.filter((part: { type?: string }) => part.type === 'text')
    .map((part: { text?: string }) => part.text)
    .join('') || '';

  let upstream: Response;
  try {
    // Call the brain's conversation endpoint
    upstream = await fetch(`${BRAIN_URL}/conversation/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(authHeader ? { Authorization: authHeader } : {}),
      },
      body: JSON.stringify({
        student_id: context?.student_id,
        message: userContent,
        track: context?.track || 'ENGLISH_LITERATURE',
        // Pass book context for contextual awareness
        current_book: context?.context?.current_book,
        highlighted_text: context?.context?.highlighted_text,
      }),
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

            // Translate FastAPI events to Data Stream Protocol
            switch (event.type) {
              case "text":
                // 0: — text delta (main content)
                enqueue(`0:${JSON.stringify(event.delta)}\n`);
                break;

              case "status":
                // 2: — data annotation
                enqueue(`2:[${JSON.stringify({ type: "status", message: event.message })}]\n`);
                break;

              case "done":
                // d: — finish marker
                enqueue(`d:${JSON.stringify({ finishReason: "stop" })}\n`);
                break;

              case "error":
                enqueue(`2:[${JSON.stringify({ type: "error", message: event.message })}]\n`);
                enqueue(`d:${JSON.stringify({ finishReason: "error" })}\n`);
                break;
            }
          }
        }
      } catch (err) {
        enqueue(`2:[${JSON.stringify({ type: "error", message: String(err) })}]\n`);
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
