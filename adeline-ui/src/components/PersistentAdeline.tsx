"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { ChevronDown, MessageCircle } from "lucide-react";
import { useStudent } from "@/lib/useStudent";
import styles from "./PersistentAdeline.module.css";

const AdelineChatPanel = dynamic(
  () => import("@/components/AdelineChatPanel").then((module) => module.AdelineChatPanel),
  { ssr: false, loading: () => <div className={styles.loading}>Adeline is getting ready…</div> },
);

export function PersistentAdeline() {
  const { student } = useStudent();
  const pathname = usePathname();
  const [minimized, setMinimized] = useState(true);

  const spacePath = pathname.match(/^\/dashboard\/spaces\/(.+)$/);
  let spacePlanItemId: string | undefined;
  if (spacePath) {
    try {
      spacePlanItemId = decodeURIComponent(spacePath[1]);
    } catch {
      spacePlanItemId = spacePath[1];
    }
  }

  // A Space's own content has no other way to advance -- open the chat
  // automatically the first time a student lands on one, instead of leaving
  // it collapsed as a bubble they may not notice they need to click.
  useEffect(() => {
    if (spacePlanItemId) setMinimized(false);
  }, [spacePlanItemId]);

  if (!student) return null;

  if (minimized) {
    return (
      <button
        type="button"
        className={styles.bubble}
        onClick={() => setMinimized(false)}
        aria-label="Open chat with Adeline"
      >
        <span className={styles.smallPortrait}>
          <Image src="/adeline-face.webp" alt="" fill sizes="44px" />
        </span>
        <MessageCircle size={18} />
      </button>
    );
  }

  return (
    <section className={styles.fixture} aria-label="Chat with Adeline">
      <div className={styles.topBar}>
        {spacePlanItemId && <span className={styles.spaceHint}>Talk here to continue this Space</span>}
        <button
          type="button"
          className={styles.toggle}
          onClick={() => setMinimized(true)}
          aria-expanded
          aria-controls="persistent-adeline-content"
        >
          <ChevronDown size={16} />
          Minimize
        </button>
      </div>

      <div id="persistent-adeline-content" className={styles.content}>
        <div className={styles.portrait}>
          <Image
            src="/adeline-face.webp"
            alt="Adeline, your learning guide"
            fill
            priority
            sizes="(max-width: 760px) 100vw, 430px"
          />
        </div>
        <div className={styles.chat}>
          <AdelineChatPanel
            studentId={student.id}
            gradeLevel={student.gradeLevel ?? "8"}
            hideHeader
            spacePlanItemId={spacePlanItemId}
          />
        </div>
      </div>
    </section>
  );
}
