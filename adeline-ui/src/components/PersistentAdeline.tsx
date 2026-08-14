"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import Image from "next/image";
import { ChevronDown, ChevronUp, MessageCircle } from "lucide-react";
import { useStudent } from "@/lib/useStudent";
import styles from "./PersistentAdeline.module.css";

const AdelineChatPanel = dynamic(
  () => import("@/components/AdelineChatPanel").then((module) => module.AdelineChatPanel),
  { ssr: false, loading: () => <div className={styles.loading}>Adeline is getting ready…</div> },
);

export function PersistentAdeline() {
  const { student } = useStudent();
  const [minimized, setMinimized] = useState(false);

  if (!student) return null;

  return (
    <section className={styles.fixture} data-minimized={minimized} aria-label="Chat with Adeline">
      <div className={styles.topBar}>
        <div className={styles.identity}>
          <span className={styles.smallPortrait}>
            <Image src="/adeline-face.webp" alt="" fill sizes="44px" />
          </span>
          <span>
            <strong>Adeline is here</strong>
            <small>Ask a question or tell her what you did today.</small>
          </span>
        </div>
        <button
          type="button"
          className={styles.toggle}
          onClick={() => setMinimized((value) => !value)}
          aria-expanded={!minimized}
          aria-controls="persistent-adeline-content"
        >
          {minimized ? <MessageCircle size={16} /> : <ChevronUp size={16} />}
          {minimized ? "Open chat" : "Minimize"}
          {minimized && <ChevronDown size={16} />}
        </button>
      </div>

      <div id="persistent-adeline-content" className={styles.content} hidden={minimized}>
        <div className={styles.portrait}>
          <Image
            src="/adeline-face.webp"
            alt="Adeline, your learning guide"
            fill
            priority
            sizes="(max-width: 760px) 100vw, 430px"
          />
          <div className={styles.portraitCaption}>
            <span>YOUR LEARNING GUIDE</span>
            <strong>What are we discovering today?</strong>
          </div>
        </div>
        <div className={styles.chat}>
          <AdelineChatPanel studentId={student.id} gradeLevel={student.gradeLevel ?? "8"} />
        </div>
      </div>
    </section>
  );
}
