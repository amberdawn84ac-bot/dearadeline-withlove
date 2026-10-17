import { afterEach, describe, expect, it, vi } from 'vitest';
vi.mock('@/lib/supabase', () => ({ supabase: { auth: { getSession: async () => ({ data: { session: null } }) } } }));
import { streamConversation } from '../brain-client';
afterEach(() => vi.unstubAllGlobals());
describe('conversation transport', () => {
  it('keeps SSE event names when network chunks split event and data lines', async () => {
    const encoder = new TextEncoder();
    const chunks = ['event: text\n', 'data: {"delta":"Matter has mass."}\n\n', 'event: done\n', 'data: {}\n\n'];
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(new ReadableStream({ start(controller) {
      chunks.forEach(chunk => controller.enqueue(encoder.encode(chunk))); controller.close();
    } }))));
    const events = [];
    for await (const event of streamConversation({ studentId: 's', message: 'What is matter?', gradeLevel: '8', history: [] })) events.push(event);
    expect(events).toEqual([{ type: 'text', delta: 'Matter has mass.' }, { type: 'done' }]);
  });
});
