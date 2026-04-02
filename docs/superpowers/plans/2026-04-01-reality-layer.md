# Reality Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a lesson-level Reality Layer that surfaces truth weights, distortion flags, keystone concepts, and attention direction to help students distinguish signal from noise.

**Architecture:** Reality layer metadata is embedded in lesson block responses from adeline-brain agents. Each block carries a weight tier (1-3) and optional distortion flags. GenUIRenderer renders these as visual components. A cross-curriculum Truth Index accumulates core truths across tracks.

**Tech Stack:** TypeScript (Zod schemas, React components), Python (reality layer service), existing GenUIRenderer and agent architecture.

---

## Task 1: Define Reality Layer Zod Types (adeline-core)

**Objective:** Add RealityLayerMetadata, WeightTier, DistortionFlag, KeystoneConcept schemas to `adeline-core/src/types.ts`.

**Details:**
- `WeightTier` enum: 1 (Core Truth), 2 (Working Knowledge), 3 (Exposure)
- `DistortionFlag` object: CommonClaim, WhatsHidden, WhatActuallyHappens, WhyItMatters
- `KeystoneConcept` object: ID, text, repetitionCount, context
- `RealityLayerMetadata` object: weightTier, distortionFlags[], keystoneConcept?, distractionBoxes[]
- Add `RealityLayerMetadata` field to `LessonBlockSchema` (optional)

**Acceptance Criteria:**
- Schemas compile without errors
- Used in both adeline-brain (Python mirrors) and adeline-ui (React components)
- Types enforce: WeightTier 1-3, distortionFlags non-empty, keystone text min 5 chars

**Code to add to `adeline-core/src/types.ts`:**

```typescript
// ══════════════════════════════════════════════════════════════════
// 6. REALITY LAYER — Truth Weights & Distortion Flags
// ══════════════════════════════════════════════════════════════════

/**
 * Weight Tiers:
 *   1 = Core Truth (red accent) — memorize + apply, fundamental to track mastery
 *   2 = Working Knowledge (amber accent) — understand well, needed for reasoning
 *   3 = Exposure (gray accent) — context only, nice-to-know background
 */
export enum WeightTier {
  CORE_TRUTH        = 1,
  WORKING_KNOWLEDGE = 2,
  EXPOSURE          = 3,
}

export const WEIGHT_TIER_LABELS: Record<WeightTier, string> = {
  [WeightTier.CORE_TRUTH]:        "Core Truth",
  [WeightTier.WORKING_KNOWLEDGE]: "Working Knowledge",
  [WeightTier.EXPOSURE]:          "Exposure",
};

export const WEIGHT_TIER_COLORS: Record<WeightTier, { bg: string; text: string; accent: string }> = {
  [WeightTier.CORE_TRUTH]:        { bg: "#FEE2E2", text: "#991B1B", accent: "#DC2626" },
  [WeightTier.WORKING_KNOWLEDGE]: { bg: "#FEF3C7", text: "#92400E", accent: "#F59E0B" },
  [WeightTier.EXPOSURE]:          { bg: "#F3F4F6", text: "#374151", accent: "#9CA3AF" },
};

/**
 * Distortion Flag: Structured call-out of what's missing or misleading in common narratives.
 * Used to flag textbook lies, propaganda, or context that gets hidden from students.
 */
export const DistortionFlagSchema = z.object({
  id:                  z.string().uuid(),
  commonClaim:         z.string().min(10).describe("The common textbook/cultural narrative"),
  whatsHidden:         z.string().min(10).describe("What gets omitted or downplayed"),
  whatActuallyHappens: z.string().min(10).describe("The real-world mechanism or truth"),
  whyItMatters:        z.string().min(5).describe("Why understanding this changes student reasoning"),
});

export type DistortionFlag = z.infer<typeof DistortionFlagSchema>;

/**
 * Keystone Concept: The one idea everything else in the lesson hangs on.
 * Repeated 3-4 times in different forms to aid retention.
 */
export const KeystonConceptSchema = z.object({
  id:               z.string().uuid(),
  concept:          z.string().min(5).describe("The core idea (e.g., 'supply and demand', 'ecosystem balance')"),
  firstIntroduced:  z.boolean().default(false).describe("Is this the first mention in the lesson?"),
  context:          z.string().optional().describe("How this concept is framed in this block"),
  repetitionNumber: z.number().int().min(1).max(4).default(1).describe("Which repeat is this? (1-4)"),
});

export type KeystoneConcept = z.infer<typeof KeystonConceptSchema>;

/**
 * DistractionBox: Explicit attention direction — what NOT to spend time on.
 * Prevents students from going down rabbit holes.
 */
export const DistractionBoxSchema = z.object({
  id:        z.string().uuid(),
  topic:     z.string().min(5).describe("What students might get sidetracked by"),
  reason:    z.string().min(10).describe("Why it's not relevant to this lesson"),
  whenToReturn: z.string().optional().describe("When/where in their education to revisit this"),
});

export type DistractionBox = z.infer<typeof DistractionBoxSchema>;

/**
 * RealityLayerMetadata: The complete reality layer for a lesson block.
 * Embedded in LessonBlockSchema as optional field.
 */
export const RealityLayerMetadataSchema = z.object({
  weightTier:       z.nativeEnum(WeightTier),
  distortionFlags:  z.array(DistortionFlagSchema).default([]).describe("Common lies to flag"),
  keystoneConcept:  KeystonConceptSchema.optional().describe("The central idea of this block"),
  distractionBoxes: z.array(DistractionBoxSchema).default([]).describe("What NOT to focus on"),
  importanceFilter: z.object({
    survivalFunction: z.boolean().describe("Does this help you survive or function in the real world?"),
    powerSystems:     z.boolean().describe("Does this reveal how power, money, or institutions work?"),
    permanence:       z.boolean().describe("Will this still be true in 50 years?"),
  }).describe("Triple filter: must pass at least one to be included"),
});

export type RealityLayerMetadata = z.infer<typeof RealityLayerMetadataSchema>;
```

Then update `LessonBlockSchema` to include the reality layer:

```typescript
export const LessonBlockSchema = z.object({
  id:         z.string().uuid(),
  lessonId:   z.string().uuid(),
  track:      z.nativeEnum(Track),
  blockType:  z.nativeEnum(BlockType),
  difficulty: z.nativeEnum(DifficultyLevel),
  order:      z.number().int().min(0),

  title:   z.string().min(1),
  content: z.string(),

  evidence:         z.array(EvidenceSchema).default([]),
  homesteadVariant: HomesteadVariantSchema.optional(),

  // NEW: Reality layer metadata
  realityLayer:     RealityLayerMetadataSchema.optional(),

  isSilenced: z.boolean().default(false),
  tags:       z.array(z.string()).default([]),
  createdAt:  z.string().datetime(),
}).superRefine((data, ctx) => {
  // ... existing validation ...
  if (data.blockType === BlockType.PRIMARY_SOURCE && data.evidence.length === 0) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ["evidence"],
      message:
        "A PRIMARY_SOURCE block must include at least one Evidence entry. " +
        "If no verified source exists, set blockType to RESEARCH_MISSION instead.",
    });
  }
});
```

---

## Task 2: Build Reality Layer Python Service (adeline-brain)

**Objective:** Create `adeline-brain/app/services/reality_layer.py` with three functions:
1. `classify_weight_tier()` — assigns 1-3 based on block content and track
2. `apply_importance_filter()` — checks if block passes Survival/Power/Permanence triple filter
3. `extract_distortion_flags()` — calls Claude to identify common claims that get hidden

**Details:**
- Import Pydantic models from `app/schemas/api_models.py` (mirrors of adeline-core types)
- Use async/await for Claude calls
- No database writes — pure computation
- Return RealityLayerMetadata object or None if block fails importance filter

**Acceptance Criteria:**
- Passes linting (pylint, black)
- Functions handle None inputs gracefully
- Distortion extraction uses Claude with temperature=0.7 (creative but not wild)
- Service integrates seamlessly into agent prompt pipelines

**Code to write at `adeline-brain/app/services/reality_layer.py`:**

```python
"""
Reality Layer Service — Classifies content into truth weights, applies importance filters,
and identifies distortion flags (common lies that students should know about).

Three-tier weight system:
  1 = Core Truth (memorize + apply)
  2 = Working Knowledge (understand well)
  3 = Exposure (context only)

Importance triple filter: Content must pass at least ONE of:
  • Survival/Function — helps you survive or function in the real world?
  • Power/Systems — reveals how power, money, or institutions actually work?
  • Permanence — will this still be true in 50 years?
"""
import uuid
import json
import logging
from typing import Optional
from datetime import datetime

import anthropic

from app.schemas.api_models import (
    BlockType, Track, RealityLayerMetadata, WeightTier,
    DistortionFlag, KeystoneConcept, DistractionBox,
)

logger = logging.getLogger(__name__)

_ANTHROPIC = anthropic.Anthropic()
_WEIGHT_TIER_PROMPT = """
You are a curriculum designer for a Christian homeschool. Classify this lesson block into one of three truth weight tiers:

1. CORE_TRUTH (memorize + apply) — Fundamental to understanding the topic. Essential for mastery.
2. WORKING_KNOWLEDGE (understand well) — Needed for reasoning through problems. Important context.
3. EXPOSURE (context only) — Nice-to-know background. Not required for competency.

Block Title: {title}
Block Type: {block_type}
Track: {track}
Content: {content}

Respond with ONLY the number (1, 2, or 3).
"""

_DISTORTION_FLAG_PROMPT = """
You are a truth-first curriculum designer. Identify common lies, propaganda, or hidden context that students often encounter about this topic. For each distortion, explain what textbooks/media claim vs. what actually happens.

Only flag distortions if they are GENUINELY misleading. If the content is straightforward, return an empty list.

Block Title: {title}
Track: {track}
Content: {content}

Respond with ONLY a JSON array of objects, each with keys:
- commonClaim (string): What textbooks/culture say
- whatsHidden (string): What gets omitted
- whatActuallyHappens (string): The real mechanism or truth
- whyItMatters (string): Why understanding this changes student reasoning

Example:
[
  {{
    "commonClaim": "Economics is a neutral science",
    "whatsHidden": "All economic systems embed assumptions about human nature and justice",
    "whatActuallyHappens": "Every economic policy benefits some groups and harms others",
    "whyItMatters": "Students must ask 'who profits?' when analyzing economic proposals"
  }}
]

If no distortions, return [].
"""

_KEYSTONE_PROMPT = """
You are a cognitive science expert. Every lesson has ONE central idea that everything else hangs on.
What is the keystone concept for this block? It should be:
- Specific enough to reference (not "math" but "compound interest")
- Applicable across multiple contexts
- Memorable in one sentence

Block Title: {title}
Content: {content}

Respond with ONLY the concept in plain text, one sentence maximum. If no clear keystone, respond with "NONE".
"""

_IMPORTANCE_FILTER_PROMPT = """
Does this lesson block pass the triple filter? It must satisfy at least ONE:

1. SURVIVAL/FUNCTION — Helps you survive or function in the real world?
2. POWER/SYSTEMS — Reveals how power, money, or institutions actually work?
3. PERMANENCE — Will this still be true in 50 years?

Block Title: {title}
Content: {content}

Respond with a JSON object:
{{
  "survivalFunction": true/false,
  "powerSystems": true/false,
  "permanence": true/false,
  "passes": true/false (true if at least one is true),
  "reasoning": "brief explanation"
}}
"""


def apply_importance_filter(title: str, content: str) -> Optional[dict]:
    """
    Apply triple filter: Survival/Function, Power/Systems, Permanence.
    Returns dict with boolean flags and passes: true if >= 1 passes.
    Returns None if the block fails (background noise).
    """
    try:
        response = _ANTHROPIC.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            messages=[
                {
                    "role": "user",
                    "content": _IMPORTANCE_FILTER_PROMPT.format(
                        title=title,
                        content=content,
                    ),
                }
            ],
            temperature=0.2,
        )

        text = response.content[0].text.strip()
        # Extract JSON from response (handle markdown code blocks)
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        result = json.loads(text)
        logger.debug(f"Importance filter for '{title}': {result}")
        return result if result.get("passes") else None

    except Exception as e:
        logger.error(f"Importance filter error for '{title}': {e}")
        return None  # Treat errors as failure (don't include ambiguous content)


def classify_weight_tier(
    title: str,
    content: str,
    block_type: str,
    track: str,
) -> int:
    """
    Classify block into WeightTier (1, 2, or 3).
    Returns int (1, 2, or 3).
    """
    try:
        response = _ANTHROPIC.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=10,
            messages=[
                {
                    "role": "user",
                    "content": _WEIGHT_TIER_PROMPT.format(
                        title=title,
                        block_type=block_type,
                        track=track,
                        content=content,
                    ),
                }
            ],
            temperature=0.2,
        )

        tier = int(response.content[0].text.strip())
        if tier not in [1, 2, 3]:
            tier = 2  # Default to WORKING_KNOWLEDGE if parse fails
        logger.debug(f"Weight tier for '{title}': {tier}")
        return tier

    except Exception as e:
        logger.error(f"Weight tier classification error for '{title}': {e}")
        return 2  # Default to WORKING_KNOWLEDGE on error


def extract_distortion_flags(title: str, track: str, content: str) -> list[DistortionFlag]:
    """
    Identify common lies, propaganda, or hidden context in this block.
    Returns list of DistortionFlag objects (empty list if none found).
    """
    try:
        response = _ANTHROPIC.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=800,
            messages=[
                {
                    "role": "user",
                    "content": _DISTORTION_FLAG_PROMPT.format(
                        title=title,
                        track=track,
                        content=content,
                    ),
                }
            ],
            temperature=0.7,
        )

        text = response.content[0].text.strip()
        # Extract JSON from response
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        flags_raw = json.loads(text)
        flags = []
        for f in flags_raw:
            flags.append(
                DistortionFlag(
                    id=str(uuid.uuid4()),
                    commonClaim=f.get("commonClaim", ""),
                    whatsHidden=f.get("whatsHidden", ""),
                    whatActuallyHappens=f.get("whatActuallyHappens", ""),
                    whyItMatters=f.get("whyItMatters", ""),
                )
            )
        logger.debug(f"Extracted {len(flags)} distortion flags for '{title}'")
        return flags

    except Exception as e:
        logger.error(f"Distortion flag extraction error for '{title}': {e}")
        return []  # Return empty list on error (don't block lesson)


def extract_keystone_concept(title: str, content: str) -> Optional[KeystoneConcept]:
    """
    Extract the single central idea everything else hangs on.
    Returns KeystoneConcept or None if no clear keystone.
    """
    try:
        response = _ANTHROPIC.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=50,
            messages=[
                {
                    "role": "user",
                    "content": _KEYSTONE_PROMPT.format(title=title, content=content),
                }
            ],
            temperature=0.2,
        )

        concept_text = response.content[0].text.strip()
        if concept_text.upper() == "NONE":
            return None

        keystone = KeystoneConcept(
            id=str(uuid.uuid4()),
            concept=concept_text,
            firstIntroduced=True,
            repetitionNumber=1,
        )
        logger.debug(f"Keystone for '{title}': {concept_text}")
        return keystone

    except Exception as e:
        logger.error(f"Keystone extraction error for '{title}': {e}")
        return None


async def build_reality_layer(
    title: str,
    content: str,
    block_type: str,
    track: str,
) -> Optional[RealityLayerMetadata]:
    """
    Build complete RealityLayerMetadata for a lesson block.

    Process:
    1. Apply importance filter (must pass at least 1/3)
    2. If passes, classify weight tier
    3. Extract distortion flags
    4. Extract keystone concept

    Returns RealityLayerMetadata or None if fails importance filter.
    """
    # Step 1: Check importance filter
    filter_result = apply_importance_filter(title, content)
    if not filter_result:
        logger.info(f"Block '{title}' failed importance filter (background noise)")
        return None

    # Step 2: Classify weight tier
    weight_tier = classify_weight_tier(title, content, block_type, track)

    # Step 3: Extract distortion flags
    distortion_flags = extract_distortion_flags(title, track, content)

    # Step 4: Extract keystone concept
    keystone = extract_keystone_concept(title, content)

    reality_layer = RealityLayerMetadata(
        weightTier=weight_tier,
        distortionFlags=distortion_flags,
        keystoneConcept=keystone,
        distractionBoxes=[],  # TODO: add distraction extraction
        importanceFilter={
            "survivalFunction": filter_result.get("survivalFunction", False),
            "powerSystems": filter_result.get("powerSystems", False),
            "permanence": filter_result.get("permanence", False),
        },
    )

    logger.info(f"Built reality layer for '{title}': tier={weight_tier}, flags={len(distortion_flags)}")
    return reality_layer
```

---

## Task 3: WeightTierBadge Component (adeline-ui)

**Objective:** Create `adeline-ui/src/components/lessons/WeightTierBadge.tsx` — a visual badge showing the truth weight tier.

**Details:**
- Red accent for Tier 1 (Core Truth)
- Amber accent for Tier 2 (Working Knowledge)
- Gray accent for Tier 3 (Exposure)
- Component takes `tier: WeightTier` prop
- Shows tier number + label + brief tooltip on hover

**Acceptance Criteria:**
- Renders correctly in all 3 tiers
- Exports TypeScript-safe component
- Used by GenUIRenderer on blocks with realityLayer

**Code to write at `adeline-ui/src/components/lessons/WeightTierBadge.tsx`:**

```typescript
"use client";

import type { WeightTier } from "@/lib/brain-client";

const TIER_STYLES: Record<WeightTier, { bg: string; text: string; label: string; tooltip: string }> = {
  1: {
    bg: "#FEE2E2",
    text: "#991B1B",
    label: "Core Truth",
    tooltip: "Memorize and apply this concept — it's fundamental to mastery.",
  },
  2: {
    bg: "#FEF3C7",
    text: "#92400E",
    label: "Working Knowledge",
    tooltip: "Understand this well — you'll need it for reasoning.",
  },
  3: {
    bg: "#F3F4F6",
    text: "#374151",
    label: "Exposure",
    tooltip: "Context only — nice to know, but not required for competency.",
  },
};

interface WeightTierBadgeProps {
  tier: WeightTier;
  showLabel?: boolean;
}

export default function WeightTierBadge({ tier, showLabel = true }: WeightTierBadgeProps) {
  const style = TIER_STYLES[tier];

  return (
    <div className="group relative">
      <span
        className="inline-flex items-center gap-1 text-xs font-bold px-2.5 py-1 rounded-full tracking-wide"
        style={{ background: style.bg, color: style.text }}
      >
        <span className="text-[10px]">●</span>
        {showLabel ? style.label : `Level ${tier}`}
      </span>

      {/* Tooltip on hover */}
      <div
        className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-1.5 bg-[#1F2937] text-white text-xs rounded whitespace-nowrap pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-200 z-50"
        style={{ fontSize: "11px" }}
      >
        {style.tooltip}
        <div
          className="absolute top-full left-1/2 transform -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-l-transparent border-r-transparent"
          style={{ borderTopColor: "#1F2937" }}
        />
      </div>
    </div>
  );
}
```

---

## Task 4: DistortionFlag Component (adeline-ui)

**Objective:** Create `adeline-ui/src/components/lessons/DistortionFlag.tsx` — renders the "what's actually true" callout box.

**Details:**
- Four-part structure: CommonClaim → WhatsHidden → WhatActuallyHappens → WhyItMatters
- Collapsible by default (shows claim + "see what's missing" button)
- Expands to show full explanation
- Red border (warning/alert color)
- Icon: ⚠️ or 🚩

**Acceptance Criteria:**
- Toggles open/closed smoothly
- Text is clear and readable
- Integrates with WeightTierBadge styling
- Exported from lessons component index

**Code to write at `adeline-ui/src/components/lessons/DistortionFlag.tsx`:**

```typescript
"use client";

import { useState } from "react";
import type { DistortionFlag as DistortionFlagType } from "@/lib/brain-client";

interface DistortionFlagProps {
  flag: DistortionFlagType;
}

export default function DistortionFlag({ flag }: DistortionFlagProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div
      className="rounded-lg p-4 border-2 space-y-2"
      style={{ borderColor: "#DC2626", background: "#FEF2F2" }}
    >
      {/* Header with toggle */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-start gap-2 text-left focus:outline-none"
      >
        <span className="text-lg shrink-0 mt-0.5">🚩</span>
        <div className="flex-1">
          <p className="text-sm font-semibold text-[#991B1B]">What you might think:</p>
          <p className="text-sm text-[#7F1D1D] leading-relaxed">{flag.commonClaim}</p>
        </div>
        <span
          className="text-xl shrink-0 transition-transform duration-200"
          style={{ transform: isOpen ? "rotate(180deg)" : "rotate(0deg)" }}
        >
          ⌄
        </span>
      </button>

      {/* Expanded content */}
      {isOpen && (
        <div className="pt-3 space-y-3 border-t border-[#DC2626]/30">
          <div>
            <p className="text-xs font-bold text-[#991B1B] uppercase tracking-wide">What's Hidden</p>
            <p className="text-sm text-[#7F1D1D] leading-relaxed mt-1">{flag.whatsHidden}</p>
          </div>

          <div>
            <p className="text-xs font-bold text-[#991B1B] uppercase tracking-wide">What Actually Happens</p>
            <p className="text-sm text-[#7F1D1D] leading-relaxed mt-1">{flag.whatActuallyHappens}</p>
          </div>

          <div>
            <p className="text-xs font-bold text-[#991B1B] uppercase tracking-wide">Why It Matters</p>
            <p className="text-sm text-[#7F1D1D] leading-relaxed mt-1">{flag.whyItMatters}</p>
          </div>
        </div>
      )}

      {!isOpen && (
        <p className="text-xs text-[#991B1B] font-semibold cursor-pointer hover:underline flex items-center gap-1">
          ↓ See what's hidden and what actually happens
        </p>
      )}
    </div>
  );
}
```

---

## Task 5: KeystoneConcept Component (adeline-ui)

**Objective:** Create `adeline-ui/src/components/lessons/KeystoneConcept.tsx` — highlights the central idea of the block.

**Details:**
- Shown at block top near title if it's the first mention
- Boxed with a prominent border and icon (🔑)
- Text bold + larger than body
- On subsequent mentions in same lesson, show inline badge instead
- Colors: gold/amber accent for visual distinction

**Acceptance Criteria:**
- Component accepts `keystone: KeystoneConcept`, `isFirstMention: boolean`
- Renders differently on first mention vs. repeats
- Styled distinctly from body text

**Code to write at `adeline-ui/src/components/lessons/KeystoneConcept.tsx`:**

```typescript
"use client";

import type { KeystoneConcept as KeystoneConceptType } from "@/lib/brain-client";

interface KeystoneConceptProps {
  keystone: KeystoneConceptType;
  isFirstMention?: boolean;
}

export default function KeystoneConcept({
  keystone,
  isFirstMention = false,
}: KeystoneConceptProps) {
  if (isFirstMention) {
    // First mention: prominent box
    return (
      <div
        className="rounded-lg p-4 border-2 border-[#F59E0B]"
        style={{ background: "#FFFBF0" }}
      >
        <div className="flex items-start gap-3">
          <span className="text-2xl shrink-0">🔑</span>
          <div className="flex-1">
            <p className="text-xs font-bold text-[#92400E] uppercase tracking-widest">Keystone Concept</p>
            <p className="text-base font-bold text-[#B45309] leading-relaxed mt-1">
              {keystone.concept}
            </p>
            {keystone.context && (
              <p className="text-sm text-[#92400E] leading-relaxed mt-2 italic">
                In this lesson: {keystone.context}
              </p>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Subsequent mentions: inline badge
  return (
    <span
      className="inline-flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-full"
      style={{ background: "#FFFBF0", color: "#B45309", border: "1px solid #F59E0B" }}
      title="This is the keystone concept mentioned earlier"
    >
      <span className="text-[10px]">🔑</span>
      {keystone.concept}
    </span>
  );
}
```

---

## Task 6: DistractionBox Component (adeline-ui)

**Objective:** Create `adeline-ui/src/components/lessons/DistractionBox.tsx` — "Don't Get Sidetracked" callout box.

**Details:**
- Yellow/caution styling
- Explicit attention direction: "Don't get distracted by X because Y"
- Optional "come back to this later" hint
- Icon: ⏸️ or 📍
- Visually distinct from DistortionFlag but same family

**Acceptance Criteria:**
- Component accepts `box: DistractionBox` prop
- Renders warning-style box
- Text clearly explains why to ignore this topic

**Code to write at `adeline-ui/src/components/lessons/DistractionBox.tsx`:**

```typescript
"use client";

import type { DistractionBox as DistractionBoxType } from "@/lib/brain-client";

interface DistractionBoxProps {
  box: DistractionBoxType;
}

export default function DistractionBox({ box }: DistractionBoxProps) {
  return (
    <div
      className="rounded-lg p-4 border-2 space-y-2"
      style={{ borderColor: "#F59E0B", background: "#FFFBF0" }}
    >
      <div className="flex items-start gap-2">
        <span className="text-lg shrink-0 mt-0.5">⏸️</span>
        <div className="flex-1">
          <p className="text-sm font-semibold text-[#92400E]">Don't get distracted by this:</p>
          <p className="text-sm text-[#B45309] leading-relaxed font-medium">{box.topic}</p>
        </div>
      </div>

      <div className="pl-6 space-y-2">
        <p className="text-xs text-[#92400E] leading-relaxed">
          <span className="font-semibold">Why not now:</span> {box.reason}
        </p>

        {box.whenToReturn && (
          <p className="text-xs text-[#B45309] italic leading-relaxed">
            <span className="font-semibold">Come back to this:</span> {box.whenToReturn}
          </p>
        )}
      </div>
    </div>
  );
}
```

---

## Task 7: Update GenUIRenderer to Render Reality Layer Components

**Objective:** Modify `adeline-ui/src/components/GenUIRenderer.tsx` to render reality layer metadata on blocks.

**Details:**
- Import WeightTierBadge, DistortionFlag, KeystoneConcept, DistractionBox
- Add reality layer rendering to each block type (PrimarySourceBlock, NarrativeBlock, etc.)
- Place WeightTierBadge next to BlockLabel
- Place DistortionFlags after block content
- Place KeystoneConcept prominently if first mention, inline if repeat
- Place DistractionBoxes before block content as warning

**Acceptance Criteria:**
- All block types render reality layer metadata if present
- Components integrate visually with existing design
- No layout breaks on blocks without reality layer
- TypeScript types correct

**Code changes to `adeline-ui/src/components/GenUIRenderer.tsx`:**

At the top, add imports:

```typescript
import WeightTierBadge from "./lessons/WeightTierBadge";
import DistortionFlag from "./lessons/DistortionFlag";
import KeystoneConcept from "./lessons/KeystoneConcept";
import DistractionBox from "./lessons/DistractionBox";
```

Update the `PrimarySourceBlock` function:

```typescript
function PrimarySourceBlock({
  block,
  isHomestead,
}: {
  block: LessonBlockResponse;
  isHomestead: boolean;
}) {
  const content =
    isHomestead && block.homestead_content ? block.homestead_content : block.content;

  return (
    <div
      className="rounded-xl p-4 space-y-3"
      style={{ background: "#FFFBF4", border: "1.5px solid #9A3F4A30" }}
    >
      {/* Header with block label + weight tier badge */}
      <div className="flex items-center justify-between gap-2">
        <BlockLabel type="PRIMARY_SOURCE" />
        {block.reality_layer && (
          <WeightTierBadge tier={block.reality_layer.weight_tier} showLabel={false} />
        )}
      </div>

      {/* Distraction boxes (if any) */}
      {block.reality_layer?.distraction_boxes && block.reality_layer.distraction_boxes.length > 0 && (
        <div className="space-y-2">
          {block.reality_layer.distraction_boxes.map((box) => (
            <DistractionBox key={box.id} box={box} />
          ))}
        </div>
      )}

      {/* Keystone concept (first mention only) */}
      {block.reality_layer?.keystone_concept &&
        block.reality_layer.keystone_concept.first_introduced && (
          <KeystoneConcept
            keystone={block.reality_layer.keystone_concept}
            isFirstMention={true}
          />
        )}

      {/* Main content */}
      <p className="text-sm text-[#2F4731] leading-relaxed whitespace-pre-wrap">{content}</p>

      {/* Distortion flags (if any) */}
      {block.reality_layer?.distortion_flags &&
        block.reality_layer.distortion_flags.length > 0 && (
          <div className="space-y-2 pt-2">
            {block.reality_layer.distortion_flags.map((flag) => (
              <DistortionFlag key={flag.id} flag={flag} />
            ))}
          </div>
        )}

      {/* Keystone concept (repeat mentions) */}
      {block.reality_layer?.keystone_concept &&
        !block.reality_layer.keystone_concept.first_introduced && (
          <div className="pt-1">
            <KeystoneConcept
              keystone={block.reality_layer.keystone_concept}
              isFirstMention={false}
            />
          </div>
        )}

      {/* Evidence footer (existing) */}
      <EvidenceFooter evidence={block.evidence} />
    </div>
  );
}
```

Apply similar pattern to `NarrativeBlock`, `LabMissionBlock`, `ExperimentBlock`, and `ResearchMissionBlock`.

---

## Task 8: Truth Index Data Model + Viewer Component

**Objective:** Create `adeline-ui/src/components/lessons/TruthIndex.tsx` — a cross-curriculum accumulator of core truths.

**Details:**
- TruthIndexEntry: concept, track, foundLessonId, definition, applications[], keyFacts[]
- Component displays scrollable list of all core truths seen so far
- Grouped by track
- Each entry shows definition + applications across other tracks
- Used in dashboard or sidebar (not inline in lessons)
- Data persists in browser localStorage or fetched from `/api/truth-index` endpoint

**Acceptance Criteria:**
- Component renders list of TruthIndexEntry objects
- Groups by track with collapsible sections
- Styled consistently with rest of app
- Exported from lessons component index

**Code to write at `adeline-ui/src/components/lessons/TruthIndex.tsx`:**

```typescript
"use client";

import { useState } from "react";
import type { Track } from "@/lib/brain-client";

export interface TruthIndexEntry {
  id: string;
  concept: string;
  track: Track;
  foundInLessonId: string;
  definition: string;
  applications: string[]; // How this appears in other tracks
  keyFacts: string[];
  seenCount: number; // How many lessons reinforce this
}

interface TruthIndexProps {
  entries: TruthIndexEntry[];
  filteredTrack?: Track;
}

export default function TruthIndex({ entries, filteredTrack }: TruthIndexProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // Filter entries by track if specified
  const filtered = filteredTrack
    ? entries.filter((e) => e.track === filteredTrack)
    : entries;

  // Group by track
  const byTrack = filtered.reduce(
    (acc, entry) => {
      if (!acc[entry.track]) acc[entry.track] = [];
      acc[entry.track].push(entry);
      return acc;
    },
    {} as Record<string, TruthIndexEntry[]>
  );

  if (Object.keys(byTrack).length === 0) {
    return (
      <div className="rounded-lg p-4 bg-[#F9FAFB] text-center text-sm text-[#6B7280]">
        No core truths indexed yet. Keep learning!
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {Object.entries(byTrack).map(([track, trackEntries]) => (
        <div key={track} className="rounded-lg border border-[#E5E7EB] overflow-hidden">
          {/* Track header */}
          <div
            className="px-4 py-3 bg-[#F3F4F6] border-b border-[#E5E7EB]"
            style={{}}
          >
            <p className="text-sm font-bold text-[#2F4731]">
              {track.replace(/_/g, " ")} ({trackEntries.length})
            </p>
          </div>

          {/* Entries */}
          <div className="space-y-0">
            {trackEntries.map((entry) => (
              <div
                key={entry.id}
                className="border-b border-[#E5E7EB] last:border-b-0"
              >
                <button
                  onClick={() =>
                    setExpandedId(expandedId === entry.id ? null : entry.id)
                  }
                  className="w-full px-4 py-3 flex items-start gap-3 text-left hover:bg-[#F9FAFB] transition-colors"
                >
                  {/* Icon */}
                  <span className="text-lg shrink-0 mt-0.5">
                    {entry.seenCount >= 3 ? "⭐" : entry.seenCount >= 1 ? "✓" : "◯"}
                  </span>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-[#1F2937]">{entry.concept}</p>
                    <p className="text-xs text-[#6B7280] mt-1">{entry.definition}</p>
                  </div>

                  {/* Repeat count */}
                  <div className="text-right shrink-0">
                    <p className="text-xs font-bold text-[#2F4731]">
                      {entry.seenCount}x
                    </p>
                    <p className="text-[10px] text-[#6B7280]">seen</p>
                  </div>
                </button>

                {/* Expanded details */}
                {expandedId === entry.id && (
                  <div className="px-4 py-3 bg-[#F9FAFB] border-t border-[#E5E7EB] space-y-2">
                    {entry.keyFacts.length > 0 && (
                      <div>
                        <p className="text-xs font-bold text-[#2F4731] uppercase tracking-wide">
                          Key Facts
                        </p>
                        <ul className="text-xs text-[#374151] mt-1 space-y-0.5 pl-4">
                          {entry.keyFacts.map((fact, i) => (
                            <li key={i} className="list-disc">
                              {fact}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {entry.applications.length > 0 && (
                      <div>
                        <p className="text-xs font-bold text-[#2F4731] uppercase tracking-wide">
                          Applications
                        </p>
                        <ul className="text-xs text-[#374151] mt-1 space-y-0.5 pl-4">
                          {entry.applications.map((app, i) => (
                            <li key={i} className="list-disc">
                              {app}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
```

Also add Python schema mirror in `adeline-brain/app/schemas/api_models.py`:

```python
class TruthIndexEntry(BaseModel):
    id: str
    concept: str
    track: str
    found_in_lesson_id: str
    definition: str
    applications: list[str] = []
    key_facts: list[str] = []
    seen_count: int = 1
```

And add endpoint to `adeline-brain/app/api/lessons.py`:

```python
@router.get("/truth-index/{student_id}")
async def get_truth_index(student_id: str):
    """
    GET /truth-index/{student_id}

    Returns all core truths (weight tier 1) indexed for this student,
    grouped by track, with application notes and repetition counts.
    """
    # Query DB for all LessonBlocks with weightTier=1 completed by student
    # Build TruthIndexEntry for each
    # Group by track
    # Return JSON array
    pass
```

---

## Self-Review Checklist

- [ ] **Zod schemas** compile without errors and are imported correctly in Python mirrors
- [ ] **Reality layer Python service** has proper error handling and logging
- [ ] **WeightTierBadge** renders correctly in all 3 tiers with tooltips
- [ ] **DistortionFlag** expands/collapses smoothly and text is readable
- [ ] **KeystoneConcept** shows prominently on first mention, as badge on repeats
- [ ] **DistractionBox** clearly explains what NOT to focus on
- [ ] **GenUIRenderer** integrates all components without breaking layout
- [ ] **TruthIndex** viewer groups by track and shows application context
- [ ] All components use consistent Tailwind styling from existing palette
- [ ] Types are correct (no `any` types)
- [ ] No database writes in pure computation functions
- [ ] Integration with existing agent prompt pipelines is clear (documented in comments)

---

## Integration Hooks (For Executor)

1. **Agent prompt enhancement:** Each agent (HistorianAgent, ScienceAgent, DiscipleshipAgent) should call `build_reality_layer()` during block synthesis and attach to LessonBlockResponse
2. **Database schema:** If persisting reality layer, add optional `realityLayer` JSONB column to `LessonBlock` table
3. **API route modification:** `/lesson/generate` should populate `reality_layer` in response blocks
4. **Frontend brain-client types:** Update `LessonBlockResponse` to include optional `reality_layer: RealityLayerMetadata` field

---

## References

- **CLAUDE.md:** Witness Protocol (0.82 threshold), 4-agent orchestration, no DB calls in algorithms
- **Types source:** `adeline-core/src/types.ts`
- **GenUIRenderer:** `adeline-ui/src/components/GenUIRenderer.tsx`
- **Agent patterns:** `adeline-brain/app/agents/orchestrator.py`
