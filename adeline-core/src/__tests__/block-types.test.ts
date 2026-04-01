import { describe, it, expect } from "vitest";
import { Track, ALL_TRACKS, BlockType, LessonBlockSchema } from "../types";
import * as enumsModule from "../enums/tracks";

describe("Track enum — canonical source", () => {
  it("has all 10 tracks in types.ts", () => {
    expect(Object.values(Track)).toHaveLength(10);
    expect(Object.values(Track)).toContain("APPLIED_MATHEMATICS");
    expect(Object.values(Track)).toContain("CREATIVE_ECONOMY");
  });

  it("ALL_TRACKS has 10 entries", () => {
    expect(ALL_TRACKS).toHaveLength(10);
  });

  it("enums/tracks.ts Track re-exports all 10 from types.ts", () => {
    expect(Object.values(enumsModule.Track)).toHaveLength(10);
    expect(enumsModule.Track).toStrictEqual(Track);
  });

  it("enums/tracks.ts ALL_TRACKS matches types.ts ALL_TRACKS", () => {
    expect(enumsModule.ALL_TRACKS).toStrictEqual(ALL_TRACKS);
  });
});

describe("BlockType enum — completeness", () => {
  it("includes all originally stored types", () => {
    expect(BlockType.TEXT).toBe("TEXT");
    expect(BlockType.PRIMARY_SOURCE).toBe("PRIMARY_SOURCE");
    expect(BlockType.LAB_MISSION).toBe("LAB_MISSION");
    expect(BlockType.RESEARCH_MISSION).toBe("RESEARCH_MISSION");
    expect(BlockType.QUIZ).toBe("QUIZ");
  });

  it("includes types used by GenUIRenderer but previously missing from enum", () => {
    expect(BlockType.NARRATIVE).toBe("NARRATIVE");
    expect(BlockType.EXPERIMENT).toBe("EXPERIMENT");
  });

  it("includes new spec block types", () => {
    expect(BlockType.DATA_TRACKING).toBe("DATA_TRACKING");
    expect(BlockType.PROBLEM).toBe("PROBLEM");
    expect(BlockType.WRITING).toBe("WRITING");
  });

  it("LessonBlockSchema accepts NARRATIVE blockType", () => {
    const result = LessonBlockSchema.safeParse({
      id: "00000000-0000-0000-0000-000000000001",
      lessonId: "00000000-0000-0000-0000-000000000002",
      track: "TRUTH_HISTORY",
      blockType: "NARRATIVE",
      difficulty: "DEVELOPING",
      order: 0,
      title: "Test Block",
      content: "Test content.",
      isSilenced: false,
      tags: [],
      createdAt: new Date().toISOString(),
    });
    expect(result.success).toBe(true);
  });

  it("LessonBlockSchema rejects unknown blockType", () => {
    const result = LessonBlockSchema.safeParse({
      id: "00000000-0000-0000-0000-000000000001",
      lessonId: "00000000-0000-0000-0000-000000000002",
      track: "TRUTH_HISTORY",
      blockType: "SCRIPTURE",
      difficulty: "DEVELOPING",
      order: 0,
      title: "Test Block",
      content: "Test content.",
      isSilenced: false,
      tags: [],
      createdAt: new Date().toISOString(),
    });
    expect(result.success).toBe(false);
  });
});
