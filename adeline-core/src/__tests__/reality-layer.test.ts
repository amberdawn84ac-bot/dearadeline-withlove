import { describe, it, expect } from "vitest";
import {
  WeightTier, WEIGHT_TIER_LABELS, WEIGHT_TIER_COLORS,
  DistortionFlagSchema, RealityLayerMetadataSchema, LessonBlockSchema,
} from "../types";

describe("WeightTier", () => {
  it("has 3 tiers", () => {
    expect(WeightTier.CORE_TRUTH).toBe(1);
    expect(WeightTier.WORKING_KNOWLEDGE).toBe(2);
    expect(WeightTier.EXPOSURE).toBe(3);
  });
  it("has labels", () => {
    expect(WEIGHT_TIER_LABELS[WeightTier.CORE_TRUTH]).toBe("Core Truth");
  });
  it("has colors", () => {
    expect(WEIGHT_TIER_COLORS[WeightTier.CORE_TRUTH].accent).toBe("#DC2626");
  });
});

describe("DistortionFlagSchema", () => {
  it("accepts valid flag", () => {
    const r = DistortionFlagSchema.safeParse({
      id: "00000000-0000-0000-0000-000000000001",
      commonClaim: "Columbus discovered America in 1492",
      whatsHidden: "Indigenous civilizations existed for thousands of years",
      whatActuallyHappens: "European colonization displaced existing nations",
      whyItMatters: "Understanding colonialism shapes policy",
    });
    expect(r.success).toBe(true);
  });
  it("rejects short commonClaim", () => {
    const r = DistortionFlagSchema.safeParse({
      id: "00000000-0000-0000-0000-000000000001",
      commonClaim: "short",
      whatsHidden: "Something hidden here that matters",
      whatActuallyHappens: "The real truth about this topic",
      whyItMatters: "It matters",
    });
    expect(r.success).toBe(false);
  });
});

describe("RealityLayerMetadataSchema", () => {
  it("accepts valid metadata", () => {
    const r = RealityLayerMetadataSchema.safeParse({
      weightTier: 1,
      distortionFlags: [],
      distractionBoxes: [],
      importanceFilter: { survivalFunction: true, powerSystems: false, permanence: true },
    });
    expect(r.success).toBe(true);
  });
  it("rejects invalid weightTier", () => {
    const r = RealityLayerMetadataSchema.safeParse({
      weightTier: 5,
      distortionFlags: [],
      distractionBoxes: [],
      importanceFilter: { survivalFunction: false, powerSystems: false, permanence: false },
    });
    expect(r.success).toBe(false);
  });
});

describe("LessonBlockSchema + realityLayer", () => {
  it("accepts block with realityLayer", () => {
    const r = LessonBlockSchema.safeParse({
      id: "00000000-0000-0000-0000-000000000001",
      lessonId: "00000000-0000-0000-0000-000000000002",
      track: "TRUTH_HISTORY", blockType: "NARRATIVE", difficulty: "EXPANDING",
      order: 0, title: "The Real Story", content: "Content",
      isSilenced: false, tags: [], createdAt: new Date().toISOString(),
      realityLayer: {
        weightTier: 1, distortionFlags: [], distractionBoxes: [],
        importanceFilter: { survivalFunction: true, powerSystems: true, permanence: false },
      },
    });
    expect(r.success).toBe(true);
  });
  it("accepts block without realityLayer", () => {
    const r = LessonBlockSchema.safeParse({
      id: "00000000-0000-0000-0000-000000000001",
      lessonId: "00000000-0000-0000-0000-000000000002",
      track: "TRUTH_HISTORY", blockType: "TEXT", difficulty: "DEVELOPING",
      order: 0, title: "Simple", content: "Content",
      isSilenced: false, tags: [], createdAt: new Date().toISOString(),
    });
    expect(r.success).toBe(true);
  });
});
