/**
 * lesson-stream.ts
 *
 * Typed data-part definitions for the /api/lesson UI Message Stream.
 *
 * The server (api/lesson/route.ts) emits newline-delimited JSON chunks whose
 * `type` field starts with "data-". The AI SDK materialises these on the client
 * as DataUIPart objects inside UIMessage.parts. Each variant is narrowed here so
 * callers never need an `as` cast.
 *
 * Stream protocol (server → client):
 *   {"type":"data-status", "data":{"message":"..."}}
 *   {"type":"data-block",  "data":{"block":{...}}}
 *   {"type":"data-done",   "data":{"title":"..."}}
 *   {"type":"data-error",  "data":{"message":"..."}}
 *
 * Usage:
 *   import { parseLessonDataParts } from '@/types/lesson-stream';
 *   const annotations = parseLessonDataParts(lastAssistant?.parts ?? []);
 */

import type { LessonBlockResponse } from '@/lib/brain-client';

// ── Typed data parts (parallel to what the server emits) ─────────────────────

export interface StatusDataPart {
  type: 'data-status';
  data: { message: string };
}

export interface BlockDataPart {
  type: 'data-block';
  data: { block: LessonBlockResponse };
}

export interface DoneDataPart {
  type: 'data-done';
  data: { title?: string };
}

export interface ErrorDataPart {
  type: 'data-error';
  data: { message: string };
}

/** Union of every lesson-specific DataUIPart variant. */
export type LessonDataPart =
  | StatusDataPart
  | BlockDataPart
  | DoneDataPart
  | ErrorDataPart;

// ── Runtime discriminated union (client-facing) ────────────────────────────────

export type LessonAnnotation =
  | { type: 'block';  block: LessonBlockResponse }
  | { type: 'done';   title?: string }
  | { type: 'status'; message: string }
  | { type: 'error';  message: string };

// ── Type-safe narrowing predicates ───────────────────────────────────────────

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v);
}

function isStatusDataPart(p: { type: string; data: unknown }): p is StatusDataPart {
  return p.type === 'data-status' && isRecord(p.data) && typeof p.data.message === 'string';
}

function isBlockDataPart(p: { type: string; data: unknown }): p is BlockDataPart {
  return p.type === 'data-block' && isRecord(p.data) && isRecord(p.data.block);
}

function isDoneDataPart(p: { type: string; data: unknown }): p is DoneDataPart {
  return p.type === 'data-done' && isRecord(p.data);
}

function isErrorDataPart(p: { type: string; data: unknown }): p is ErrorDataPart {
  return p.type === 'data-error' && isRecord(p.data) && typeof p.data.message === 'string';
}

/** Unwrap an AI SDK v6 DataUIPart ({ type: "data", data: {...} }) to the inner lesson payload. */
function unwrapDataPart(p: unknown): { type: string; data: unknown } | null {
  if (!isRecord(p) || typeof p.type !== 'string') return null;

  // AI SDK v6 wraps custom data as { type: "data", data: <payload> }
  if (p.type === 'data' && isRecord(p.data) && typeof p.data.type === 'string') {
    return p.data as { type: string; data: unknown };
  }

  // Direct lesson data part (fallback)
  if (p.type.startsWith('data-')) {
    return p as { type: string; data: unknown };
  }

  return null;
}

/** Narrow a raw UIPart[] to LessonAnnotation[].
 *  Handles AI SDK v6 DataUIPart wrapping ({ type: "data", data: {...} }).
 */
export function parseLessonDataParts(parts: unknown[]): LessonAnnotation[] {
  const out: LessonAnnotation[] = [];
  for (const p of parts) {
    const inner = unwrapDataPart(p);
    if (!inner) continue;

    if (isBlockDataPart(inner))  { out.push({ type: 'block',  block: inner.data.block }); continue; }
    if (isDoneDataPart(inner))   { out.push({ type: 'done',   title: inner.data.title }); continue; }
    if (isStatusDataPart(inner)) { out.push({ type: 'status', message: inner.data.message }); continue; }
    if (isErrorDataPart(inner))  { out.push({ type: 'error',  message: inner.data.message }); continue; }
  }
  return out;
}

/** @deprecated Use parseLessonDataParts directly. Kept for backward compat. */
export function isLessonDataPart(p: unknown): boolean {
  return unwrapDataPart(p) !== null;
}

/** Convenience: extract only the text content from a UIMessage parts array. */
export function extractTextParts(parts: unknown[]): string {
  return parts
    .filter((p): p is { type: 'text'; text: string } =>
      isRecord(p) && p.type === 'text' && typeof p.text === 'string',
    )
    .map((p) => p.text)
    .join('');
}
