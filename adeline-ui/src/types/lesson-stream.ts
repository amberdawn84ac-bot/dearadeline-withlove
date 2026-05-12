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

/** Narrows any raw UIPart to one of the four lesson data-part variants. */
export function isLessonDataPart(p: unknown): p is LessonDataPart {
  if (!isRecord(p) || typeof p.type !== 'string' || !p.type.startsWith('data-')) return false;
  const candidate = p as { type: string; data: unknown };
  return (
    isStatusDataPart(candidate) ||
    isBlockDataPart(candidate) ||
    isDoneDataPart(candidate) ||
    isErrorDataPart(candidate)
  );
}

/** Narrow a raw UIPart[] to the typed LessonDataPart[] then map to LessonAnnotation[]. */
export function parseLessonDataParts(parts: unknown[]): LessonAnnotation[] {
  const out: LessonAnnotation[] = [];
  for (const p of parts) {
    if (!isLessonDataPart(p)) continue;
    if (isBlockDataPart(p))  { out.push({ type: 'block',  block: p.data.block }); continue; }
    if (isDoneDataPart(p))   { out.push({ type: 'done',   title: p.data.title }); continue; }
    if (isStatusDataPart(p)) { out.push({ type: 'status', message: p.data.message }); continue; }
    if (isErrorDataPart(p))  { out.push({ type: 'error',  message: p.data.message }); continue; }
  }
  return out;
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
