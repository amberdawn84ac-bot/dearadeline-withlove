"use client";

import { useState } from "react";
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
  // Visible by default -- Today and every other non-Space page has no other
  // way to reach Adeline, so starting collapsed made her look like she'd
  // disappeared from the page entirely.
  const [minimized, setMinimized] = useState(false);

  const spacePath = pathname.match(/^\/dashboard\/spaces\/(.+)$/);
  let spacePlanItemId: string | undefined;
  if (spacePath) {
    try {
      spacePlanItemId = decodeURIComponent(spacePath[1]);
    } catch {
      spacePlanItemId = spacePath[1];
    }
  }

  // A unit Space is itself an Adeline conversation. It renders its own
  // full-page chat, so the global floating chat must not duplicate it.
  if (!student || spacePlanItemId) return null;

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
          />
        </div>
      </div>
    </section>
  );
}
