'use client';

import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import { useStudent } from '@/lib/useStudent';
import { getLearningPlan, streamConversation } from '@/lib/brain-client';
import type { ConversationMessage, LessonSuggestion } from '@/lib/brain-client';
import styles from '@/components/nav/sites-dashboard.module.css';

const ADELINE_FACE =
  'https://raw.githubusercontent.com/amberdawn84ac-bot/dearadeline-withlove/main/adeline-world/public/adeline-face.png';

type ChatMessage = { role: 'adeline' | 'learner'; text: string };

const FALLBACK_STARTERS = [
  'Strengthen measurement with a greenhouse challenge',
  'Show me another learning gap',
  'I’d like to do something different',
];

export default function DashboardPage() {
  const { student, loading: studentLoading } = useStudent();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [streamingReply, setStreamingReply] = useState('');
  const [isThinking, setIsThinking] = useState(false);
  const [error, setError] = useState('');
  const [suggestions, setSuggestions] = useState<LessonSuggestion[]>([]);
  const [planLoading, setPlanLoading] = useState(true);

  const studentId = student?.id ?? '';
  const gradeLevel = student?.gradeLevel ?? '8';

  const loadPlan = useCallback(async () => {
    if (!studentId) return;
    setPlanLoading(true);
    try {
      const plan = await getLearningPlan(studentId, 6);
      setSuggestions(plan.suggestions ?? []);
    } catch (reason) {
      console.error('[Dashboard] Could not load learning plan:', reason);
      setSuggestions([]);
    } finally {
      setPlanLoading(false);
    }
  }, [studentId]);

  useEffect(() => {
    if (studentId) void loadPlan();
  }, [studentId, loadPlan]);

  const heroSuggestion = suggestions[0];
  const heroTitle = heroSuggestion
    ? heroSuggestion.title
    : 'You’re close on measurement conversions.';
  const heroDescription = heroSuggestion?.description
    || 'When we planned the greenhouse, switching feet to inches slowed you down. Want to tackle that through a quick design challenge, or would you like to do something different?';

  const starterPrompts = useMemo(() => {
    if (!suggestions.length) return FALLBACK_STARTERS;
    const fromPlan = suggestions.slice(0, 2).map((suggestion) => suggestion.title);
    return [...fromPlan, 'I’d like to do something different'];
  }, [suggestions]);

  async function send(text: string) {
    const value = text.trim();
    if (!value || !studentId || isThinking) return;

    const history: ConversationMessage[] = messages.map((message) => ({
      role: message.role === 'learner' ? 'user' : 'adeline',
      content: message.text,
    }));

    setMessages((current) => [...current, { role: 'learner', text: value }]);
    setInput('');
    setError('');
    setStreamingReply('');
    setIsThinking(true);

    let completeReply = '';
    try {
      for await (const event of streamConversation({
        studentId,
        message: value,
        gradeLevel,
        history,
      })) {
        if (event.type === 'text' && event.delta) {
          completeReply += event.delta;
          setStreamingReply(completeReply);
        } else if (event.type === 'block') {
          const blockText = [event.title, event.content].filter(Boolean).join('\n');
          if (blockText) {
            completeReply += `${completeReply ? '\n\n' : ''}${blockText}`;
            setStreamingReply(completeReply);
          }
        } else if (event.type === 'error') {
          throw new Error(event.message || 'Adeline could not answer yet.');
        }
      }

      const finalReply = completeReply.trim();
      if (finalReply) {
        setMessages((current) => [...current, { role: 'adeline', text: finalReply }]);
      }
      setStreamingReply('');
    } catch (reason) {
      setStreamingReply('');
      setError(reason instanceof Error ? reason.message : 'Adeline could not answer yet.');
    } finally {
      setIsThinking(false);
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void send(input);
  }

  if (studentLoading) {
    return <div className={styles.loading}>Opening today&apos;s adventure…</div>;
  }

  if (!student) {
    return <div className={styles.loading}>Your session has ended. Please sign in again.</div>;
  }

  return (
    <div>
      <section className={styles.hero} id="talk-to-adeline">
        <div className={styles.adelineArt}>
          <img src={ADELINE_FACE} alt="Adeline" />
        </div>
        <div className={styles.heroCopy}>
          <p className={styles.eyebrow}>I noticed something we can strengthen…</p>
          <h1>{heroTitle}</h1>
          <span className={styles.heroText}>{heroDescription}</span>
          <div className={styles.starters}>
            {starterPrompts.map((starter) => (
              <button key={starter} type="button" disabled={isThinking} onClick={() => void send(starter)}>
                {starter}
              </button>
            ))}
          </div>
        </div>
      </section>

      {(messages.length > 0 || streamingReply || isThinking) && (
        <section className={styles.chat} aria-live="polite" aria-busy={isThinking}>
          {messages.map((message, index) => (
            <p
              key={`${message.role}-${index}`}
              className={message.role === 'learner' ? styles.learnerMessage : styles.adelineMessage}
            >
              {message.text}
            </p>
          ))}
          {streamingReply && <p className={styles.adelineMessage}>{streamingReply}</p>}
          {isThinking && !streamingReply && <p className={styles.adelineMessage}>Adeline is thinking…</p>}
        </section>
      )}

      {error && <p className={styles.error} role="alert">{error}</p>}

      <form className={styles.composer} onSubmit={submit}>
        <label htmlFor="dashboard-message">Message Adeline</label>
        <textarea
          id="dashboard-message"
          rows={2}
          value={input}
          disabled={isThinking}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Tell Adeline what you’re thinking…"
        />
        <button type="submit" disabled={isThinking || !input.trim()}>
          {isThinking ? 'Thinking…' : 'Ask →'}
        </button>
      </form>

      <section className={styles.today} aria-label="Today's learning plan">
        <div className={styles.todayHeader}>
          <div>
            <p>Chosen for where you are today</p>
            <h2>Your next adventures</h2>
          </div>
          <a href="/dashboard/resource-vault">Explore the Resource Vault</a>
        </div>

        {planLoading ? (
          <div className={styles.loading}>Adeline is checking your learning path…</div>
        ) : (
          <div className={styles.cards}>
            {suggestions.slice(0, 6).map((suggestion) => (
              <button
                key={suggestion.id}
                type="button"
                className={styles.card}
                onClick={() => void send(`I want to work on: ${suggestion.title}`)}
              >
                <small>{suggestion.track.replace(/_/g, ' ')}</small>
                <h3>{suggestion.emoji} {suggestion.title}</h3>
                <p>{suggestion.description}</p>
              </button>
            ))}
            {!suggestions.length && (
              <button type="button" className={styles.card} onClick={() => void send('Help me choose something meaningful to learn today.') }>
                <small>Start with wonder</small>
                <h3>Ask Adeline what to explore</h3>
                <p>Your learning plan grows from your interests, your work, and the skills you still need for graduation.</p>
              </button>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
