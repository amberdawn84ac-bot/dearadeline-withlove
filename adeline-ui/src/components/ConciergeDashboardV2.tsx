'use client';

import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';
import { BookOpen, MessageCircle, Send } from 'lucide-react';
import { reportActivity } from '@/lib/brain-client';
import type { ActivityReportResponse, ConversationMessage } from '@/lib/brain-client';
import { streamAdelineConversation } from '@/lib/conversation-client';
import SketchnoteCard, { type SketchnoteData } from '@/components/SketchnoteCard';
import { saveSketchnote } from '@/lib/journal-client';

type Props = { studentId: string; studentName: string; gradeLevel: string };
type ActivityEvidence = ActivityReportResponse & {
  standard_codes?: string[];
  concepts_demonstrated?: string[];
  concepts_to_explore?: string[];
};
type ChatMessage = {
  id: string;
  role: 'user' | 'adeline';
  text: string;
  evidence?: ActivityEvidence;
  sketchNote?: SketchnoteData;
};

const ACTIVITY_RE = /\b(?:i|we)\s+(?:baked|cooked|made|built|fixed|repaired|started|planted|grew|harvested|read|wrote|researched|studied|practiced|helped|volunteered|sewed|crocheted|knitted|painted|drew|tested|measured|mixed|fed|trained|cleaned|worked|designed|coded|created|visited|went|learned|tried|finished|worked on|took care of)\b/i;

function makeId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
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

  async function quietlyRecordActivity(description: string) {
    if (!ACTIVITY_RE.test(description)) return;

    try {
      const result = (await reportActivity({
        student_id: studentId,
        grade_level: gradeLevel,
        description,
      } as Parameters<typeof reportActivity>[0])) as ActivityEvidence;

      setMessages((prev) => [
        ...prev,
        {
          id: makeId(),
          role: 'adeline',
          text: '',
          evidence: result,
        },
      ]);
    } catch {
      // Recording is backstage. It must never derail the conversation.
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
    let hadError = false;

    try {
      for await (const event of streamAdelineConversation({
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
          hadError = true;
          const message = /401|403|auth/i.test(event.message)
            ? 'I lost your sign-in connection. Refresh this page and try me again.'
            : 'I can’t reach my Brain right now. Try that once more in a moment.';
          responseText = message;
          setMessages((prev) =>
            prev.map((item) => item.id === streamingId ? { ...item, text: message } : item),
          );
        }
      }

      if (!hadError && responseText.trim()) {
        const turns: ConversationMessage[] = [
          { role: 'user', content: text },
          { role: 'adeline', content: responseText },
        ];
        setHistory((prev) => [...prev, ...turns].slice(-24));
        void quietlyRecordActivity(text);
      }
    } catch {
      setMessages((prev) =>
        prev.map((message) =>
          message.id === streamingId
            ? { ...message, text: 'I can’t reach my Brain right now. Try that once more in a moment.' }
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
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4">
          <div>
            <p className="text-[10px] uppercase tracking-[.22em] text-[#8b7b66]">Adeline</p>
            <h1 className="text-3xl text-[#213f2d]" style={{ fontFamily: 'var(--font-emilys-candy)' }}>I&apos;m here.</h1>
          </div>
          <Link href="/dashboard/daily-bread" className="inline-flex items-center gap-2 rounded-full border border-[#cdbf9e] bg-[#fffdf7] px-4 py-2 text-xs font-semibold text-[#5f513e] shadow-sm hover:bg-white">
            <BookOpen size={15} /> Daily Bread
          </Link>
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
                {!message.text && busy && !message.evidence && <p>…</p>}
                {message.sketchNote && (
                  <SketchnoteCard
                    note={message.sketchNote}
                    onSave={() => saveSketchnote(studentId, message.sketchNote!)}
                  />
                )}
                {message.evidence && <EvidenceReceipt evidence={message.evidence} />}
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
            Conversation first. Adeline maps real life to standards quietly underneath.
          </p>
        </div>
      </div>
    </main>
  );
}

function EvidenceReceipt({ evidence }: { evidence: ActivityEvidence }) {
  const concepts = evidence.concepts_demonstrated ?? [];
  const standards = evidence.standard_codes ?? [];
  const next = evidence.concepts_to_explore ?? [];

  return (
    <div className="mt-2 rounded-xl border border-[#cdbf9e] bg-[#f6edd9] px-3 py-2 text-[11px] text-[#6f624f]">
      <p className="font-semibold text-[#355642]">Saved to your learning record</p>
      <p className="mt-1">{evidence.course_title}</p>
      {concepts.length > 0 && <p className="mt-1 text-[#796b58]">Evidence: {concepts.slice(0, 4).join(' · ')}</p>}
      {standards.length > 0 && <p className="mt-1 text-[10px] text-[#8b7b67]">{standards.length} state standard{standards.length === 1 ? '' : 's'} connected</p>}
      {next.length > 0 && <p className="mt-1 italic text-[#7a5f45]">A natural next thread: {next[0]}</p>}
    </div>
  );
}
