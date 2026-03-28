"use client";

import { clsx } from "clsx";

type BlockType =
  | "NARRATIVE"
  | "QUESTION"
  | "ACTIVITY"
  | "SKETCHNOTE"
  | "RESEARCH_MISSION"
  | "SCRIPTURE"
  | "DEFINITION";

interface LessonBlock {
  blockId: string;
  blockType: BlockType;
  content: string;
  isSilenced: boolean;
  homesteadContent?: string;
  evidence?: { sourceTitle: string; similarityScore: number }[];
}

interface GenUIRendererProps {
  lessonId: string;
  blocks: LessonBlock[];
  isHomestead: boolean;
}

// ── Block Renderers ────────────────────────────────────────────────────────────

function NarrativeBlock({ block, isHomestead }: { block: LessonBlock; isHomestead: boolean }) {
  const content = isHomestead && block.homesteadContent ? block.homesteadContent : block.content;
  return (
    <div className="sketch-card space-y-2">
      <BlockLabel type="NARRATIVE" />
      <p className="font-body text-fuschia leading-relaxed">{content}</p>
    </div>
  );
}

function QuestionBlock({ block }: { block: LessonBlock }) {
  return (
    <div className="sketch-card border-l-4 border-papaya space-y-2">
      <BlockLabel type="QUESTION" />
      <p className="font-sketch text-lg text-paradise">{block.content}</p>
      <textarea
        className="w-full mt-2 p-2 bg-parchment-50 border border-fuschia font-body text-sm
                   resize-none focus:outline-none focus:ring-1 focus:ring-papaya"
        rows={3}
        placeholder="Write your thoughts here..."
      />
    </div>
  );
}

function ActivityBlock({ block }: { block: LessonBlock }) {
  return (
    <div className="sketch-card border-2 border-dashed border-papaya space-y-2">
      <BlockLabel type="ACTIVITY" />
      <p className="font-body text-fuschia">{block.content}</p>
    </div>
  );
}

function SketchnoteBlock({ block }: { block: LessonBlock }) {
  return (
    <div className="sketch-card bg-parchment-200 space-y-3">
      <BlockLabel type="SKETCHNOTE" />
      <p className="font-sketch text-fuschia">{block.content}</p>
      <div
        className="w-full h-48 border-2 border-fuschia bg-parchment-50
                   flex items-center justify-center text-papaya font-sketch text-sm"
      >
        [ Sketchnote Canvas — Draw Here ]
      </div>
    </div>
  );
}

function ResearchMissionBlock({ block }: { block: LessonBlock }) {
  return (
    <div className="witness-alert space-y-2 rounded">
      <div className="flex items-center gap-2">
        <span className="text-xl">&#128269;</span>
        <BlockLabel type="RESEARCH_MISSION" />
      </div>
      <p className="font-body text-sm text-fuschia whitespace-pre-line">{block.content}</p>
    </div>
  );
}

function ScriptureBlock({ block }: { block: LessonBlock }) {
  return (
    <div className="sketch-card border-paradise bg-parchment-200 text-center space-y-1">
      <BlockLabel type="SCRIPTURE" />
      <blockquote className="font-sketch text-paradise italic text-lg px-4">
        &ldquo;{block.content}&rdquo;
      </blockquote>
    </div>
  );
}

function DefinitionBlock({ block }: { block: LessonBlock }) {
  const [term, ...rest] = block.content.split(":");
  return (
    <div className="sketch-card flex gap-3">
      <BlockLabel type="DEFINITION" />
      <div>
        <span className="font-sketch text-papaya font-bold">{term}:</span>
        <span className="font-body text-fuschia ml-1">{rest.join(":").trim()}</span>
      </div>
    </div>
  );
}

// ── Block Label ────────────────────────────────────────────────────────────────

const BLOCK_LABEL_STYLES: Record<BlockType, string> = {
  NARRATIVE: "bg-fuschia text-parchment-50",
  QUESTION: "bg-papaya text-parchment-50",
  ACTIVITY: "bg-paradise text-parchment-50",
  SKETCHNOTE: "bg-papaya-dark text-parchment-50",
  RESEARCH_MISSION: "bg-paradise text-parchment-50",
  SCRIPTURE: "bg-paradise-light text-parchment-50",
  DEFINITION: "bg-fuschia-light text-parchment-50",
};

function BlockLabel({ type }: { type: BlockType }) {
  return (
    <span
      className={clsx(
        "inline-block text-xs font-sketch px-2 py-0.5 uppercase tracking-widest rounded-sm",
        BLOCK_LABEL_STYLES[type]
      )}
    >
      {type.replace(/_/g, " ")}
    </span>
  );
}

// ── GenUIRenderer ─────────────────────────────────────────────────────────────

export default function GenUIRenderer({ lessonId: _lessonId, blocks, isHomestead }: GenUIRendererProps) {
  return (
    <div className="space-y-4">
      {blocks.map((block) => {
        if (block.isSilenced) return null;

        switch (block.blockType) {
          case "NARRATIVE":
            return <NarrativeBlock key={block.blockId} block={block} isHomestead={isHomestead} />;
          case "QUESTION":
            return <QuestionBlock key={block.blockId} block={block} />;
          case "ACTIVITY":
            return <ActivityBlock key={block.blockId} block={block} />;
          case "SKETCHNOTE":
            return <SketchnoteBlock key={block.blockId} block={block} />;
          case "RESEARCH_MISSION":
            return <ResearchMissionBlock key={block.blockId} block={block} />;
          case "SCRIPTURE":
            return <ScriptureBlock key={block.blockId} block={block} />;
          case "DEFINITION":
            return <DefinitionBlock key={block.blockId} block={block} />;
          default:
            return null;
        }
      })}
    </div>
  );
}
