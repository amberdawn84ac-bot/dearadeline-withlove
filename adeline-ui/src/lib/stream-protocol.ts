/**
 * Data Stream Protocol parser — Vercel AI SDK compatible.
 *
 * Parses the line-prefixed protocol emitted by the Next.js lesson route
 * (which translates brain SSE into Data Stream Protocol format).
 *
 * Line prefixes:
 *   0:"text"                     → text-delta
 *   2:[{type:"genui_skeleton",...}] → data annotation (GenUI payloads, status)
 *   9:{toolCallId:...}           → tool-call-streaming-start
 *   c:{toolCallId:...}           → tool-call (complete)
 *   a:{toolCallId:...}           → tool-result
 *   d:{finishReason:"stop"}      → finish-message
 *   e:{finishReason:...}         → finish-step
 *
 * This parser is used by useGenUIStream to process the raw stream and
 * extract GenUI component state for progressive rendering.
 */

// ── Parsed event types ─────────────────────────────────────────────────────

export type DataStreamEvent =
  | { prefix: "0"; delta: string }
  | { prefix: "2"; annotations: DataAnnotation[] }
  | { prefix: "9"; toolCallId: string; toolName: string; args: Record<string, unknown> }
  | { prefix: "c"; toolCallId: string; toolName: string; args: Record<string, unknown> }
  | { prefix: "a"; toolCallId: string; result: unknown }
  | { prefix: "d"; finishReason: string }
  | { prefix: "e"; finishReason: string };

export type DataAnnotation =
  | GenUISkeletonAnnotation
  | GenUIPropsAnnotation
  | GenUICompleteAnnotation
  | RemediationAnnotation
  | StatusAnnotation
  | BlockAnnotation
  | DoneAnnotation;

export interface GenUISkeletonAnnotation {
  type: "genui_skeleton";
  componentId: string;
  componentType: string;
  props: null;
  state: "skeleton";
  hints?: Record<string, unknown>;
  lessonId?: string;
  track?: string;
}

export interface GenUIPropsAnnotation {
  type: "genui_props";
  componentId: string;
  props: Record<string, unknown>;
  state: "partial" | "complete";
}

export interface GenUICompleteAnnotation {
  type: "genui_complete";
  componentId: string;
  componentType: string;
  props: Record<string, unknown>;
  state: "complete";
  callbacks?: string[];
  initialState?: Record<string, unknown>;
  lessonId?: string;
  track?: string;
}

export interface RemediationAnnotation {
  type: "remediation";
  remedialId: string;
  sourceComponentId: string;
  componentType: string;
  props: Record<string, unknown>;
  reason: string;
}

export interface StatusAnnotation {
  type: "status";
  message: string;
}

export interface BlockAnnotation {
  type: "data-block";
  data: { block: Record<string, unknown> };
}

export interface DoneAnnotation {
  type: "data-done";
  data: { title: string; lesson_id?: string };
}

// ── Parser ────────────────────────────────────────────────────────────────

/**
 * Parse a single Data Stream Protocol line into a typed event.
 * Returns null for unrecognized or malformed lines.
 */
export function parseDataStreamLine(line: string): DataStreamEvent | null {
  if (line.length < 2 || line[1] !== ":") return null;

  const prefix = line[0];
  const payload = line.slice(2);

  try {
    switch (prefix) {
      case "0": {
        const delta = JSON.parse(payload) as string;
        return { prefix: "0", delta };
      }
      case "2": {
        const annotations = JSON.parse(payload) as DataAnnotation[];
        return { prefix: "2", annotations };
      }
      case "9": {
        const data = JSON.parse(payload) as {
          toolCallId: string;
          toolName: string;
          args: Record<string, unknown>;
        };
        return { prefix: "9", ...data };
      }
      case "c": {
        const data = JSON.parse(payload) as {
          toolCallId: string;
          toolName: string;
          args: Record<string, unknown>;
        };
        return { prefix: "c", ...data };
      }
      case "a": {
        const data = JSON.parse(payload) as {
          toolCallId: string;
          result: unknown;
        };
        return { prefix: "a", ...data };
      }
      case "d": {
        const data = JSON.parse(payload) as { finishReason: string };
        return { prefix: "d", ...data };
      }
      case "e": {
        const data = JSON.parse(payload) as { finishReason: string };
        return { prefix: "e", ...data };
      }
      default:
        return null;
    }
  } catch {
    return null;
  }
}

/**
 * Async generator that reads a ReadableStream and yields parsed events.
 */
export async function* parseDataStream(
  stream: ReadableStream<Uint8Array>,
): AsyncGenerator<DataStreamEvent> {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        const event = parseDataStreamLine(trimmed);
        if (event) yield event;
      }
    }
  } finally {
    reader.releaseLock();
  }
}
