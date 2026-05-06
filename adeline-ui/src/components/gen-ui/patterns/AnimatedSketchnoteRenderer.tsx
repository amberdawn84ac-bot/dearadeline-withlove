"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import type {
  AnimatedSketchnoteLesson,
  AnimatedScene,
  VisualElement,
  AnimationInstruction,
  StyledText,
} from "@/lib/brain-client";

// ── Typography style → CSS class mapping ─────────────────────────────────────

const STYLE_CLASS: Record<string, string> = {
  bold_marker:  "font-kranky text-2xl font-black tracking-tight",
  block_caps:   "font-mono text-sm font-bold uppercase tracking-widest",
  script_hand:  "font-kalam text-lg italic",
  sketch_print: "font-kalam text-base",
  tiny_notes:   "font-mono text-xs opacity-70",
  label:        "font-mono text-xs font-semibold uppercase",
  caption:      "font-kalam text-sm italic opacity-80",
};

// ── Animation → framer-motion variant mapping ─────────────────────────────────

function getAnimationVariant(anim: string) {
  switch (anim) {
    case "write_on":
    case "draw_in":   return { hidden: { opacity: 0, pathLength: 0 }, visible: { opacity: 1, pathLength: 1 } };
    case "fade_in":   return { hidden: { opacity: 0 }, visible: { opacity: 1 } };
    case "pop_in":    return { hidden: { opacity: 0, scale: 0 }, visible: { opacity: 1, scale: 1 } };
    case "slide_in":  return { hidden: { opacity: 0, x: -40 }, visible: { opacity: 1, x: 0 } };
    case "zoom_in":   return { hidden: { opacity: 0, scale: 0.5 }, visible: { opacity: 1, scale: 1 } };
    case "pulse":     return { hidden: { opacity: 1 }, visible: { opacity: [1, 0.4, 1] } };
    case "wiggle":    return { hidden: { rotate: 0 }, visible: { rotate: [0, -5, 5, -3, 3, 0] } };
    case "highlight": return { hidden: { backgroundColor: "transparent" }, visible: { backgroundColor: "#BD680930" } };
    default:          return { hidden: { opacity: 0 }, visible: { opacity: 1 } };
  }
}

function getEasing(easing?: string): import("framer-motion").Easing {
  switch (easing) {
    case "ease_in":     return "easeIn";
    case "ease_out":    return "easeOut";
    case "ease_in_out": return "easeInOut";
    default:            return "linear";
  }
}

// ── StyledText renderer ───────────────────────────────────────────────────────

function StyledTextBlock({ st }: { st: StyledText }) {
  const cls = STYLE_CLASS[st.style] ?? "font-kalam text-base";
  return (
    <span
      className={cls}
      style={{ color: "inherit" }}
      data-emphasis={st.emphasis}
    >
      {st.text}
    </span>
  );
}

// ── Visual element renderer ───────────────────────────────────────────────────

function VisualElementItem({
  el,
  instruction,
  playing,
}: {
  el: VisualElement;
  instruction?: AnimationInstruction;
  playing: boolean;
}) {
  const anim = instruction?.animation ?? "fade_in";
  const variant = getAnimationVariant(anim);
  const delay = instruction ? instruction.startTime : 0;
  const duration = instruction ? instruction.duration : 0.6;
  const ease = instruction ? getEasing(instruction.easing) : "easeOut";

  const left = `${el.position.x}%`;
  const top = `${el.position.y}%`;
  const width = el.size ? `${el.size.width}%` : undefined;
  const height = el.size ? `${el.size.height}%` : undefined;

  const typeCls: Record<string, string> = {
    arrow:          "text-[#BD6809] text-2xl select-none pointer-events-none",
    bubble:         "border-2 border-[#9A3F4A] rounded-2xl px-3 py-1 bg-[#FFFEF7]",
    label:          "text-xs font-mono font-bold uppercase text-[#3D1419]",
    doodle:         "opacity-70",
    handwritten_text: "font-kalam",
    icon:           "text-3xl select-none",
    character:      "text-4xl select-none",
    background:     "opacity-20",
    diagram:        "border border-[#BD6809] rounded p-2 bg-[#FFFEF7]/80",
    split_screen:   "border-l-2 border-[#9A3F4A] pl-2",
    timeline:       "border-t-2 border-[#BD6809] pt-1",
  };

  return (
    <motion.div
      key={el.id}
      className={`absolute ${typeCls[el.type] ?? ""} ${STYLE_CLASS[el.style ?? "sketch_print"] ?? ""}`}
      style={{
        left, top, width, height,
        color: el.color ?? "#3D1419",
        maxWidth: width ?? "80%",
      }}
      initial="hidden"
      animate={playing ? "visible" : "hidden"}
      variants={variant}
      transition={{ delay, duration, ease }}
    >
      {el.content}
    </motion.div>
  );
}

// ── Scene renderer ────────────────────────────────────────────────────────────

function SceneView({
  scene,
  playing,
  audioRef,
}: {
  scene: AnimatedScene;
  playing: boolean;
  audioRef: React.RefObject<HTMLAudioElement | null>;
}) {
  const instrMap = new Map(
    scene.animationPlan.map((inst) => [inst.elementId, inst])
  );

  useEffect(() => {
    if (!audioRef.current) return;
    if (playing && scene.narrationAudioUrl) {
      audioRef.current.src = scene.narrationAudioUrl;
      audioRef.current.play().catch(() => {});
    } else {
      audioRef.current.pause();
    }
  }, [playing, scene.narrationAudioUrl, audioRef]);

  return (
    <div className="relative w-full h-full bg-[#FFFEF7] overflow-hidden rounded-xl">
      {scene.visualBuild.map((el) => (
        <VisualElementItem
          key={el.id}
          el={el}
          instruction={instrMap.get(el.id)}
          playing={playing}
        />
      ))}
    </div>
  );
}

// ── Teaching layer sidebar ────────────────────────────────────────────────────

function TeachingLayer({ scene }: { scene: AnimatedScene }) {
  const tl = scene.teachingLayer as {
    visualSummary?: StyledText[];
    deepExplanation?: StyledText;
    whyItMatters?: StyledText;
    activity?: StyledText;
  };

  return (
    <div className="flex flex-col gap-4 text-[#3D1419]">
      {tl.visualSummary && tl.visualSummary.length > 0 && (
        <div className="flex flex-col gap-1">
          <span className="font-mono text-xs uppercase tracking-widest text-[#BD6809] mb-1">
            Key Points
          </span>
          {tl.visualSummary.map((st, i) => (
            <div key={i} className="flex gap-2 items-start">
              <span className="text-[#BD6809] mt-0.5">▸</span>
              <StyledTextBlock st={st} />
            </div>
          ))}
        </div>
      )}

      {tl.deepExplanation && (
        <div>
          <span className="font-mono text-xs uppercase tracking-widest text-[#9A3F4A] mb-1 block">
            Deep Dive
          </span>
          <StyledTextBlock st={tl.deepExplanation} />
        </div>
      )}

      {tl.whyItMatters && (
        <div className="border-l-4 border-[#BD6809] pl-3">
          <span className="font-mono text-xs uppercase tracking-widest text-[#BD6809] mb-1 block">
            Why It Matters
          </span>
          <StyledTextBlock st={tl.whyItMatters} />
        </div>
      )}

      {tl.activity && (
        <div className="bg-[#BD6809]/10 rounded-xl p-3 border border-[#BD6809]/30">
          <span className="font-mono text-xs uppercase tracking-widest text-[#BD6809] mb-1 block">
            Try It
          </span>
          <StyledTextBlock st={tl.activity} />
        </div>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface Props {
  lesson: AnimatedSketchnoteLesson;
}

export default function AnimatedSketchnoteRenderer({ lesson }: Props) {
  const [currentScene, setCurrentScene] = useState(0);
  const [playing, setPlaying] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const scene = lesson.scenes[currentScene];
  const totalScenes = lesson.scenes.length;

  // Auto-advance after scene duration
  useEffect(() => {
    if (!playing) return;
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => {
      if (currentScene < totalScenes - 1) {
        setCurrentScene((s) => s + 1);
      } else {
        setPlaying(false);
      }
    }, scene.durationSeconds * 1000);
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [playing, currentScene, scene.durationSeconds, totalScenes]);

  function handleSceneSelect(i: number) {
    setCurrentScene(i);
    setPlaying(false);
  }

  function handlePlayPause() {
    setPlaying((p) => !p);
  }

  return (
    <div
      className="rounded-2xl overflow-hidden border border-[#BD6809]/30 bg-[#FFFEF7] shadow-lg"
      style={{ fontFamily: "var(--font-kalam), cursive" }}
    >
      {/* Header */}
      <div className="bg-[#3D1419] px-6 py-4 flex items-center justify-between">
        <div>
          <h2 className="text-[#FFFEF7] font-kranky text-2xl">
            {lesson.title.text}
          </h2>
          <p className="text-[#BD6809] font-kalam text-sm mt-0.5">
            {lesson.subtitle.text}
          </p>
        </div>
        <div className="text-right">
          <span className="text-[#FFFEF7]/60 font-mono text-xs block">
            Scene {currentScene + 1} / {totalScenes}
          </span>
          <span className="text-[#BD6809] font-mono text-xs">
            {Math.round(lesson.totalDurationSeconds / 60)} min
          </span>
        </div>
      </div>

      {/* Main content */}
      <div className="flex flex-col lg:flex-row gap-0">
        {/* Canvas */}
        <div className="flex-1 min-h-[360px] relative">
          <AnimatePresence mode="wait">
            <motion.div
              key={currentScene}
              className="absolute inset-0"
              initial={{ opacity: 0, x: 30 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -30 }}
              transition={{ duration: 0.4 }}
            >
              <SceneView scene={scene} playing={playing} audioRef={audioRef} />
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Teaching layer sidebar */}
        <div className="lg:w-72 bg-[#FFFEF7] border-t lg:border-t-0 lg:border-l border-[#BD6809]/20 p-5 overflow-y-auto max-h-[420px]">
          <div className="font-kranky text-[#3D1419] text-lg mb-3">
            {scene.sceneTitle.text}
          </div>
          <TeachingLayer scene={scene} />
        </div>
      </div>

      {/* Controls */}
      <div className="bg-[#3D1419]/5 border-t border-[#BD6809]/20 px-4 py-3 flex items-center gap-3">
        {/* Play/Pause */}
        <button
          onClick={handlePlayPause}
          className="w-10 h-10 rounded-full bg-[#3D1419] text-[#FFFEF7] flex items-center justify-center hover:bg-[#9A3F4A] transition-colors"
          aria-label={playing ? "Pause" : "Play"}
        >
          {playing ? "⏸" : "▶"}
        </button>

        {/* Scene dots */}
        <div className="flex gap-1.5 flex-1">
          {lesson.scenes.map((s, i) => (
            <button
              key={i}
              onClick={() => handleSceneSelect(i)}
              className={`rounded-full transition-all ${
                i === currentScene
                  ? "w-5 h-3 bg-[#BD6809]"
                  : "w-3 h-3 bg-[#3D1419]/20 hover:bg-[#BD6809]/50"
              }`}
              aria-label={`Scene ${i + 1}`}
            />
          ))}
        </div>

        {/* Scene duration */}
        <span className="font-mono text-xs text-[#3D1419]/50">
          {scene.durationSeconds}s
        </span>
      </div>

      {/* Narration text (accessible) */}
      <div className="px-5 pb-4 pt-2 border-t border-[#BD6809]/10">
        <p className="font-kalam text-sm text-[#3D1419]/70 italic leading-relaxed">
          {scene.narration}
        </p>
      </div>

      {/* Hidden audio element */}
      <audio ref={audioRef} className="hidden" />
    </div>
  );
}
