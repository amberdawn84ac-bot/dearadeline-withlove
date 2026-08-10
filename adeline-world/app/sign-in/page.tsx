"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  authenticateStudent,
  getPlayerSession,
  savePlayerSession,
  StudentAuthError,
} from "../lib/player-session";

export default function SignInPage() {
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [pin, setPin] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [gradeLevel, setGradeLevel] = useState("3-5");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (getPlayerSession()) router.replace("/dashboard");
  }, [router]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);

    try {
      const body: Record<string, string> = { username: username.trim().toLowerCase(), pin };
      if (mode === "register") {
        body.display_name = displayName.trim();
        body.grade_level = gradeLevel;
      }
      let session;
      try {
        session = await authenticateStudent(mode, body);
      } catch (reason) {
        if (mode !== "register" || !(reason instanceof StudentAuthError) || reason.status !== 409) {
          throw reason;
        }

        // A prior interrupted registration may already have created this player.
        // If the same PIN works, safely resume that existing identity.
        try {
          session = await authenticateStudent("login", { username: body.username, pin });
        } catch {
          // The Brain also uses 409 for its rare generated link-code collision.
          // One fresh registration attempt generates a new code; a second conflict
          // means the chosen username belongs to another player.
          try {
            session = await authenticateStudent("register", body);
          } catch (retryReason) {
            if (retryReason instanceof StudentAuthError && retryReason.status === 409) {
              throw new StudentAuthError(
                "That username is already in use. Choose another username or switch to Sign in.",
                409,
              );
            }
            throw retryReason;
          }
        }
      }
      savePlayerSession(session);
      router.push("/dashboard");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Adeline could not sign you in.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <Link className="auth-back" href="/">← Dear Adeline</Link>
        <div className="auth-welcome">
          <img src="/adeline-face.png" alt="Adeline" />
          <div>
            <p>Welcome to your learning adventure</p>
            <h1>{mode === "login" ? "Come on in!" : "Create your player"}</h1>
          </div>
        </div>

        <div className="auth-tabs" role="tablist" aria-label="Player access">
          <button className={mode === "login" ? "active" : ""} onClick={() => setMode("login")} type="button">Sign in</button>
          <button className={mode === "register" ? "active" : ""} onClick={() => setMode("register")} type="button">New player</button>
        </div>

        <form onSubmit={submit}>
          {mode === "register" && (
            <>
              <label>What should Adeline call you?<input required autoComplete="name" value={displayName} onChange={(event) => setDisplayName(event.target.value)} /></label>
              <label>Learning level<select value={gradeLevel} onChange={(event) => setGradeLevel(event.target.value)}><option>K-2</option><option>3-5</option><option>6-8</option><option>9-12</option></select></label>
            </>
          )}
          <label>Player username<input required autoCapitalize="none" autoComplete="username" minLength={3} maxLength={20} pattern="[a-z0-9_]+" title="Use lowercase letters, numbers, or underscores" value={username} onChange={(event) => setUsername(event.target.value.toLowerCase().replace(/[^a-z0-9_]/g, ""))} /></label>
          <label>4-digit PIN<input required type="password" inputMode="numeric" autoComplete={mode === "login" ? "current-password" : "new-password"} pattern="[0-9]{4}" maxLength={4} value={pin} onChange={(event) => setPin(event.target.value.replace(/\D/g, "").slice(0, 4))} /></label>
          {error && <p className="auth-error" role="alert">{error}</p>}
          <button className="auth-submit" disabled={busy} type="submit">{busy ? "Opening your adventure…" : mode === "login" ? "Enter Dear Adeline" : "Start my adventure"}</button>
        </form>

        <p className="auth-note">Use the same username and PIN in AdelineMobile. Your learning, game progress, portfolio, and transcript stay with one student identity.</p>
      </section>
    </main>
  );
}
