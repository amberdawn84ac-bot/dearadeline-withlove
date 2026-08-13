'use client';

import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react';
import { useStudent } from '@/lib/useStudent';
import { getLearningPlan, streamConversation, streamLesson } from '@/lib/brain-client';
import type { ConversationMessage, LessonBlockResponse, LessonResponse, LessonSuggestion, Track } from '@/lib/brain-client';
import LessonRenderer from '@/components/lessons/LessonRenderer';
import styles from '@/components/nav/sites-dashboard.module.css';

const ADELINE_FACE = '/adeline-face.webp';

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
  const [activeLesson, setActiveLesson] = useState<LessonResponse | null>(null);
  const [lessonBlocks, setLessonBlocks] = useState<LessonBlockResponse[]>([]);
  const [lessonStatus, setLessonStatus] = useState('');
  const [isGeneratingLesson, setIsGeneratingLesson] = useState(false);
  const [lastLearnerTopic, setLastLearnerTopic] = useState('');

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
    setLastLearnerTopic(value);
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

  async function generateLesson(topic: string, track: Track = 'TRUTH_HISTORY') {
    const value = topic.trim();
    if (!value || !studentId || isGeneratingLesson) return;

    setError('');
    setActiveLesson(null);
    setLessonBlocks([]);
    setLessonStatus('Adeline is gathering the right sources…');
    setIsGeneratingLesson(true);
    const collected: LessonBlockResponse[] = [];

    try {
      for await (const event of streamLesson({
        student_id: studentId,
        topic: value,
        track,
        grade_level: gradeLevel,
        is_homestead: track === 'HOMESTEADING',
      })) {
        if (event.type === 'status') {
          setLessonStatus(event.message);
        } else if (event.type === 'block') {
          collected.push(event.block);
          setLessonBlocks([...collected]);
        } else if (event.type === 'done') {
          setActiveLesson({
            lesson_id: event.lesson_id,
            title: event.title || value,
            track,
            blocks: collected,
            has_research_missions: collected.some((block) => block.block_type === 'RESEARCH_MISSION'),
            researcher_activated: collected.some((block) => block.block_type === 'PRIMARY_SOURCE'),
            oas_standards: (event.oas_standards as LessonResponse['oas_standards']) ?? [],
            agent_name: 'Adeline',
            xapi_statements: [],
            credits_awarded: event.credits_awarded ?? [],
          });
          setLessonBlocks([]);
          setLessonStatus('');
          await loadPlan();
        } else if (event.type === 'error') {
          throw new Error(event.message || 'Adeline could not build this lesson yet.');
        }
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Adeline could not build this lesson yet.');
    } finally {
      setIsGeneratingLesson(false);
      setLessonStatus('');
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

      {messages.some((message) => message.role === 'adeline') && !activeLesson && !isGeneratingLesson && (
        <div className={styles.lessonPrompt}>
          <div>
            <strong>Ready to turn this into real learning?</strong>
            <span>Adeline will build the lesson, choose useful sources, and connect completed work to the learning record.</span>
          </div>
          <button type="button" onClick={() => void generateLesson(lastLearnerTopic || heroTitle, heroSuggestion?.track ?? 'TRUTH_HISTORY')}>
            Build my lesson →
          </button>
        </div>
      )}

      {(isGeneratingLesson || activeLesson) && (
        <section className={styles.generatedLesson} aria-live="polite">
          {lessonStatus && <p className={styles.lessonStatus}>{lessonStatus}</p>}
          {isGeneratingLesson && lessonBlocks.length === 0 && (
            <div className={styles.loading}>Adeline is building a complete lesson—not another chat answer…</div>
          )}
          {lessonBlocks.length > 0 && (
            <LessonRenderer
              lesson={{
                lesson_id: 'streaming', title: lastLearnerTopic, track: heroSuggestion?.track ?? 'TRUTH_HISTORY',
                blocks: lessonBlocks, has_research_missions: false, researcher_activated: false,
                agent_name: '', xapi_statements: [], credits_awarded: [], oas_standards: [],
              }}
              studentId={studentId}
            />
          )}
          {activeLesson && <LessonRenderer lesson={activeLesson} studentId={studentId} />}
        </section>
      )}

      <section className={styles.today} aria-label="Today's learning plan">
        <div className={styles.todayHeader}>
          <div>
            <p>Chosen for where you are today</p>
            <h2>Your next adventures</h2>
          </div>
          <span>Adeline chooses sources when they are useful</span>
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
                onClick={() => void generateLesson(
                  suggestion.description ? `${suggestion.title}: ${suggestion.description}` : suggestion.title,
                  suggestion.track,
                )}
                disabled={isGeneratingLesson}
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
