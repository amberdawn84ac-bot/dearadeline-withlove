"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { getPlayerSession, PlayerProfile } from "../lib/player-session";
import DashboardNav from "./DashboardNav";

type Message = { role: "adeline" | "learner"; text: string };

const starters = [
  "Strengthen measurement with a greenhouse challenge",
  "Show me another learning gap",
  "I’d like to do something different",
];

function readSseEvent(block: string) {
  let event = "message";
  const data: string[] = [];

  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    if (line.startsWith("data:")) data.push(line.slice(5).trim());
  }

  return { event, data: data.join("\n") };
}

export default function Dashboard() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streamingReply, setStreamingReply] = useState("");
  const [isThinking, setIsThinking] = useState(false);
  const [error, setError] = useState("");
  const [player, setPlayer] = useState<PlayerProfile | null>(null);

  useEffect(() => {
    const session = getPlayerSession();
    if (!session) {
      window.location.assign("/sign-in");
      return;
    }
    const frame = window.requestAnimationFrame(() => setPlayer(session.player));
    return () => window.cancelAnimationFrame(frame);
  }, []);

  async function send(text: string) {
    const value = text.trim();
    const session = getPlayerSession();
    if (!value || isThinking || !session) return;

    const history = messages.map((message) => ({
      role: message.role === "learner" ? "user" : "assistant",
      content: message.text,
    }));

    setMessages((current) => [...current, { role: "learner", text: value }]);
    setInput("");
    setError("");
    setStreamingReply("");
    setIsThinking(true);

    try {
      const response = await fetch("/api/brain/brain/conversation/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session.token}`,
        },
        body: JSON.stringify({
          student_id: session.studentId,
          message: value,
          grade_level: session.player.grade_level ?? "8",
          conversation_history: history,
        }),
      });

      if (!response.ok || !response.body) {
        const payload = await response.json().catch(() => ({}));
        throw new Error(typeof payload.detail === "string" ? payload.detail : "Adeline could not answer yet.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let completeReply = "";

      while (true) {
        const { value: chunk, done } = await reader.read();
        buffer += decoder.decode(chunk, { stream: !done });

        let boundary = buffer.indexOf("\n\n");
        while (boundary !== -1) {
          const rawEvent = buffer.slice(0, boundary);
          buffer = buffer.slice(boundary + 2);
          const { event, data } = readSseEvent(rawEvent);

          if (event === "text" && data) {
            const payload = JSON.parse(data) as { delta?: string };
            if (payload.delta) {
              completeReply += payload.delta;
              setStreamingReply(completeReply);
            }
          } else if (event === "error") {
            const payload = JSON.parse(data) as { message?: string };
            throw new Error(payload.message || "Adeline could not answer yet.");
          }

          boundary = buffer.indexOf("\n\n");
        }

        if (done) break;
      }

      const finalReply = completeReply.trim();
      if (!finalReply) throw new Error("Adeline returned an empty response.");
      setMessages((current) => [...current, { role: "adeline", text: finalReply }]);
      setStreamingReply("");
    } catch (cause) {
      setStreamingReply("");
      setError(cause instanceof Error ? cause.message : "Adeline could not answer yet.");
    } finally {
      setIsThinking(false);
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    void send(input);
  }

  const initials = player?.display_name
    ? player.display_name.split(/\s+/).map((part) => part[0]).join("").slice(0, 2).toUpperCase()
    : "AR";

  return (
    <main className="dashboard-page">
      <header className="dashboard-header">
        <Link href="/">Dear Adeline</Link>
        <span>Today’s adventure</span>
        <button type="button" aria-label="Learner profile">{initials}</button>
      </header>

      <div className="dashboard-layout">
        <DashboardNav active="today" />

        <div className="dashboard-main" id="today">
          <section className="dashboard-hero" id="talk-to-adeline">
            <div className="dashboard-adeline">
              <img src="/adeline-face.png" alt="Adeline" />
            </div>
            <div>
              <p>I noticed something we can strengthen…</p>
              <h1>You’re close on measurement conversions.</h1>
              <span>
                When we planned the greenhouse, switching feet to inches slowed you down.
                Want to tackle that through a quick design challenge—or would you like to do something different?
              </span>
              <div className="dashboard-starters">
                {starters.map((starter) => (
                  <button key={starter} type="button" disabled={isThinking} onClick={() => void send(starter)}>{starter}</button>
                ))}
              </div>
            </div>
          </section>

          {(messages.length > 0 || streamingReply || isThinking) && (
            <section className="dashboard-chat" aria-live="polite" aria-busy={isThinking}>
              {messages.map((message, index) => (
                <p className={message.role} key={`${message.role}-${index}`}>{message.text}</p>
              ))}
              {streamingReply && <p className="adeline">{streamingReply}</p>}
              {isThinking && !streamingReply && <p className="adeline">Adeline is thinking…</p>}
            </section>
          )}

          {error && <p className="dashboard-chat-error" role="alert">{error}</p>}

          <form className="dashboard-composer" onSubmit={submit}>
            <label htmlFor="dashboard-message">Message Adeline</label>
            <textarea
              id="dashboard-message"
              rows={2}
              value={input}
              disabled={isThinking}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Tell Adeline what you’re thinking…"
            />
            <button type="submit" disabled={isThinking || !input.trim()}>{isThinking ? "Thinking…" : "Ask →"}</button>
          </form>
        </div>
      </div>
    </main>
  );
}
