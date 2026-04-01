import { describe, it, expect } from "vitest";
import { Track, ALL_TRACKS } from "../types";
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
