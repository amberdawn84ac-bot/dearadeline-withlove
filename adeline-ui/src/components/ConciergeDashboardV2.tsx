'use client';

import { useEffect, useRef, useState } from 'react';
import { MessageCircle, Send } from 'lucide-react';
import { reportActivity, streamConversation } from '@/lib/brain-client';
import type { ActivityReportResponse, ConversationMessage } from '@/lib/brain-client';
import SketchnoteCard, { type SketchnoteData } from '@/components/SketchnoteCard';
import { saveSketchnote } from '@/lib/journal-client';

type Props = { studentId: string; studentName: string; gradeLevel: string };
type ChatMessage = {
  id: string;
  role: 'user' | 'adeline';
  text: string;
  credit?: ActivityReportResponse;
  sketchNote?: SketchnoteData;
};

const ACTIVITY_RE = /\b(i (spent|did|worked|practiced|baked|built|planted|made|helped|cooked|studied|read|drew|painted|sewed|fixed|repaired|cleaned|volunteered)|today i|this (morning|afternoon|evening|week)|i've been|we (built|fixed|made|worked|planted|cooked|repaired))\b/i;

function makeId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function parseMinutes(text: string): number | null {
  const hours = text.match(/(\d+(?:\.\d+)?)\s*hour/i);
  const minutes = text.match(/(\d+)\s*min/i);
  if (/\ban hour\b/i.test(text) && !hours) return 60;
  if (/half.{0,5}hour/i.test(text) && !minutes) return 30;
  let total = 0;
  if (hours) total += Number(hours[1]) * 60;
  if (minutes) total += Number(minutes[1]);
  return total > 0 ? Math.round(total) : null;
}

function normalizeSketchnote(block: Record<string, unknown>): SketchnoteData {
  const rawSections = Array.isArray(block.sections) ? block.sections : [];
  return {
    title: typeof block.title === 'string' ? block.title : 'Something worth keeping',
    big_idea: typeof block.big_idea === 'string' ? block.big_idea : undefined,
    sections: rawSections
      .slice(0, 6)
      .map((item) => {
        const section = item && typeof item === 'object' ? (item as Record<string, unknown>) : {};
        return {
          heading: typeof section.heading === 'string' ? section.heading : 'Note',
          text: typeof section.text === 'string' ? section.text : '',
          symbol: typeof section.symbol === 'string' ? section.symbol : undefined,
        };
      })
      .filter((section) => section.text),
    keywords: Array.isArray(block.keywords)
      ? block.keywords.filter((word): word is string => typeof word === 'string').slice(0, 8)
      : [],
    footer: typeof block.footer === 'string' ? block.footer : undefined,
    track: typeof block.track === 'string' ? block.track : undefined,
  };
}

export default function ConciergeDashboardV2({ studentId, studentName, gradeLevel }: Props) {
  const firstName = studentName?.trim().split(/\s+/)[0] || 'there';
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'adeline',
      text: `Hey ${firstName}. What have you been up to? You can tell me anything.`,
    },
  ]);
  const [history, setHistory] = useState<ConversationMessage[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, busy]);

  async function quietlyFileActivity(description: string) {
    const minutes = parseMinutes(description);
    if (!ACTIVITY_RE.test(description) || !minutes) return;

    try {
      const result = await reportActivity({
        student_id: studentId,
        grade_level: gradeLevel,
        description,
        time_minutes: minutes,
      });

      setMessages((prev) => [
        ...prev,
        {
          id: makeId(),
          role: 'adeline',
          text: 'I saved that to your learning record.',
          credit: result,
        },
      ]);
    } catch {
      // Filing is secondary. A record problem must never derail the conversation.
    }
  }

  async function send() {
    const text = input.trim();
    if (!text || busy) return;

    setInput('');
    setMessages((prev) => [...prev, { id: makeId(), role: 'user', text }]);
    setBusy(true);

    const streamingId = makeId();
    setMessages((prev) => [...prev, { id: streamingId, role: 'adeline', text: '' }]);

    let responseText = '';

    try {
      for await (const event of streamConversation({
        studentId,
        message: text,
        gradeLevel,
        history,
      })) {
        if (event.type === 'text') {
          responseText += event.delta;
          setMessages((prev) =>
            prev.map((message) =>
              message.id === streamingId ? { ...message, text: responseText } : message,
            ),
          );
        } else if (event.type === 'block' && event.block_type === 'SKETCHNOTE_NOTE') {
          const note = normalizeSketchnote(event as Record<string, unknown>);
          setMessages((prev) =>
            prev.map((message) =>
              message.id === streamingId ? { ...message, sketchNote: note } : message,
            ),
          );
        } else if (event.type === 'block') {
          const addition = [
            typeof event.title === 'string' ? event.title : '',
            typeof event.content === 'string' ? event.content : '',
          ]
            .filter(Boolean)
            .join('\n');
          responseText += `${responseText ? '\n\n' : ''}${addition}`;
          setMessages((prev) =>
            prev.map((message) =>
              message.id === streamingId ? { ...message, text: responseText } : message,
            ),
          );
        } else if (event.type === 'error') {
          responseText = 'I lost the thread for a second. Tell me that again?';
          setMessages((prev) =>
            prev.map((message) =>
              message.id === streamingId ? { ...message, text: responseText } : message,
            ),
          );
        }
      }

      const turns: ConversationMessage[] = [
        { role: 'user', content: text },
        { role: 'adeline', content: responseText },
      ];
      setHistory((prev) => [...prev, ...turns].slice(-24));

      void quietlyFileActivity(text);
    } catch {
      setMessages((prev) =>
        prev.map((message) =>
          message.id === streamingId
            ? { ...message, text: 'Something tripped over itself. Try that once more.' }
            : message,
        ),
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="flex min-h-[100dvh] flex-col bg-[#fbf7ec] text-[#243a2a] lg:h-screen lg:min-h-0">
      <header className="border-b border-[#d9cfbb] bg-[#f7f1e4]/85 px-5 py-4 backdrop-blur sm:px-8">
        <div className="mx-auto max-w-5xl">
          <p className="text-[10px] uppercase tracking-[.22em] text-[#8b7b66]">Adeline</p>
          <h1 className="font-serif text-2xl text-[#213f2d]">I&apos;m here.</h1>
        </div>
      </header>

      <section className="flex-1 overflow-y-auto px-4 py-6 sm:px-8">
        <div className="mx-auto max-w-5xl space-y-6">
          {messages.map((message) => (
            <div
              key={message.id}
              className={message.role === 'user' ? 'flex justify-end' : 'flex justify-start'}
            >
              <div
                className={
                  message.role === 'user'
                    ? 'max-w-[82%] rounded-[22px_22px_5px_22px] bg-[#244a35] px-4 py-3 text-sm leading-relaxed text-[#fffaf0]'
                    : 'max-w-[92%] rounded-[5px_22px_22px_22px] border border-[#ded2bc] bg-[#fffdf7] px-4 py-3 text-sm leading-relaxed text-[#354b3b] shadow-[0_5px_18px_rgba(74,57,35,.05)]'
                }
              >
                {message.text && <p className="whitespace-pre-wrap">{message.text}</p>}
                {!message.text && busy && <p>…</p>}
                {message.sketchNote && (
                  <SketchnoteCard
                    note={message.sketchNote}
                    onSave={() => saveSketchnote(studentId, message.sketchNote!)}
                  />
                )}
                {message.credit && (
                  <div className="mt-3 rounded-xl border border-[#cdbf9e] bg-[#f6edd9] px-3 py-2 text-[11px] text-[#6f624f]">
                    {message.credit.course_title} · {message.credit.credit_hours} credit hrs
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      </section>

      <div className="border-t border-[#d9cfbb] bg-[#f7f1e4] px-4 py-4 sm:px-8">
        <div className="mx-auto max-w-5xl">
          <div className="flex items-end gap-3 rounded-[24px_18px_24px_18px] border border-[#cfc2ab] bg-[#fffdf7] p-3 shadow-[0_8px_24px_rgba(67,51,31,.07)]">
            <MessageCircle className="mb-2 hidden text-[#9c7a39] sm:block" size={18} />
            <textarea
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                  event.preventDefault();
                  void send();
                }
              }}
              rows={2}
              placeholder="Tell Adeline anything..."
              className="min-h-[52px] flex-1 resize-none bg-transparent px-1 py-2 text-sm outline-none placeholder:text-[#9a8b76]"
            />
            <button
              onClick={() => void send()}
              disabled={!input.trim() || busy}
              aria-label="Send"
              className="mb-1 flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[#9a4d71] text-white transition hover:scale-[1.03] disabled:opacity-35"
            >
              <Send size={16} />
            </button>
          </div>
          <p className="mt-2 text-center text-[10px] text-[#8c7c67]">
            Conversation first. Adeline keeps the learning record quietly underneath.
          </p>
        </div>
      </div>
    </main>
  );
}
