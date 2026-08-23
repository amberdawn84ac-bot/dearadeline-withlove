'use client';

import { FormEvent, useState } from 'react';
import { Loader2, MessageCircle, Send, Sparkles } from 'lucide-react';
import { askParentAdeline, type ParentAdelineTurn } from '@/lib/parent-client';

const STARTERS = [
  'What has everyone been learning lately?',
  'What could we do together this weekend?',
  'Where is each child making progress?',
  'Give us a meaningful low-cost family project.',
];

export function ParentAdelinePanel() {
  const [messages, setMessages] = useState<ParentAdelineTurn[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function ask(message: string) {
    const clean = message.trim();
    if (!clean || loading) return;
    const history = messages;
    setMessages([...history, { role: 'parent', content: clean }]);
    setInput('');
    setLoading(true);
    setError(null);
    try {
      const response = await askParentAdeline(clean, history);
      setMessages((current) => [...current, { role: 'adeline', content: response }]);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Adeline could not answer just now.');
    } finally {
      setLoading(false);
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void ask(input);
  }

  return (
    <section className="overflow-hidden rounded-[28px] border border-[#CFC1A8] bg-[#294735] text-white shadow-[0_18px_50px_rgba(47,71,49,.12)]">
      <div className="grid gap-8 p-6 sm:p-8 lg:grid-cols-[.8fr_1.2fr]">
        <div>
          <p className="flex items-center gap-2 text-xs font-black uppercase tracking-[.18em] text-[#E8B65A]">
            <Sparkles className="h-4 w-4" /> Parent ↔ Adeline
          </p>
          <h2 className="mt-3 text-3xl font-bold" style={{ fontFamily: 'var(--font-emilys-candy), cursive' }}>
            Ask about the family&rsquo;s learning
          </h2>
          <p className="mt-3 max-w-lg text-sm leading-6 text-white/72">
            This is a parent conversation with family-level context. It is separate from every child&rsquo;s private learning conversation.
          </p>
          <div className="mt-5 flex flex-wrap gap-2">
            {STARTERS.map((starter) => (
              <button
                key={starter}
                type="button"
                onClick={() => void ask(starter)}
                disabled={loading}
                className="rounded-full border border-white/20 bg-white/8 px-3 py-2 text-left text-xs font-semibold text-white/90 transition hover:border-[#E8B65A] hover:bg-white/12 disabled:opacity-50"
              >
                {starter}
              </button>
            ))}
          </div>
        </div>

        <div className="rounded-2xl bg-[#FFFDF6] p-4 text-[#2F4731] sm:p-5">
          <div className="max-h-72 space-y-3 overflow-y-auto pr-1" aria-live="polite">
            {messages.length === 0 && (
              <div className="flex min-h-32 items-center justify-center gap-3 text-center text-sm text-[#2F4731]/55">
                <MessageCircle className="h-6 w-6 text-[#BD6809]" />
                Ask what the family has discovered, what is emerging, or what to try next.
              </div>
            )}
            {messages.map((message, index) => (
              <div
                key={`${message.role}-${index}`}
                className={`rounded-2xl px-4 py-3 text-sm leading-6 ${message.role === 'parent' ? 'ml-8 bg-[#EAD9BB]' : 'mr-8 border border-[#E7DAC3] bg-white'}`}
              >
                <p className="mb-1 text-[10px] font-black uppercase tracking-[.14em] text-[#2F4731]/45">
                  {message.role === 'parent' ? 'You' : 'Adeline'}
                </p>
                <p className="whitespace-pre-wrap">{message.content}</p>
              </div>
            ))}
            {loading && (
              <div className="mr-8 flex items-center gap-2 rounded-2xl border border-[#E7DAC3] bg-white px-4 py-3 text-sm text-[#2F4731]/60">
                <Loader2 className="h-4 w-4 animate-spin text-[#BD6809]" /> Adeline is reading the family&rsquo;s learning record…
              </div>
            )}
          </div>
          {error && <p className="mt-3 text-xs font-semibold text-[#9A3F4A]" role="alert">{error}</p>}
          <form onSubmit={submit} className="mt-4 flex gap-2">
            <label htmlFor="parent-adeline-question" className="sr-only">Ask parent-facing Adeline</label>
            <input
              id="parent-adeline-question"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              maxLength={4000}
              placeholder="What would you like to understand?"
              className="min-w-0 flex-1 rounded-xl border border-[#CFC1A8] bg-white px-4 py-3 text-sm outline-none transition focus:border-[#BD6809] focus:ring-2 focus:ring-[#BD6809]/15"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              aria-label="Send question"
              className="grid h-12 w-12 shrink-0 place-items-center rounded-xl bg-[#BD6809] text-white transition hover:bg-[#9A3F4A] disabled:opacity-40"
            >
              <Send className="h-4 w-4" />
            </button>
          </form>
        </div>
      </div>
    </section>
  );
}
