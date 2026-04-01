import { describe, it, expect } from "vitest";
import { Track, ALL_TRACKS } from "../types";
import { TRACK_CREDIT_MAP } from "../config/tracks";
import { CreditBucket } from "../schemas/standards";

describe("TRACK_CREDIT_MAP", () => {
  it("has an entry for all 10 tracks", () => {
    for (const track of ALL_TRACKS) {
      expect(TRACK_CREDIT_MAP[track], `Missing entry for ${track}`).toBeDefined();
    }
  });

  it("every entry has a non-empty externalName", () => {
    for (const [track, mapping] of Object.entries(TRACK_CREDIT_MAP)) {
      expect(
        mapping.externalName.length,
        `${track} externalName is empty`
      ).toBeGreaterThan(0);
    }
  });

  it("every primary CreditBucket is a valid CreditBucket value", () => {
    const validBuckets = Object.values(CreditBucket);
    for (const [track, mapping] of Object.entries(TRACK_CREDIT_MAP)) {
      expect(
        validBuckets,
        `${track} primary bucket "${mapping.primary}" is not a valid CreditBucket`
      ).toContain(mapping.primary);
    }
  });

  it("APPLIED_MATHEMATICS maps to MATH bucket", () => {
    expect(TRACK_CREDIT_MAP[Track.APPLIED_MATHEMATICS].primary).toBe(CreditBucket.MATH);
  });

  it("CREATIVE_ECONOMY maps to FINE_ARTS bucket", () => {
    expect(TRACK_CREDIT_MAP[Track.CREATIVE_ECONOMY].primary).toBe(CreditBucket.FINE_ARTS);
  });

  it("ENGLISH_LITERATURE maps to ENGLISH bucket", () => {
    expect(TRACK_CREDIT_MAP[Track.ENGLISH_LITERATURE].primary).toBe(CreditBucket.ENGLISH);
  });

  it("OSRHE dashboard tracks total at least 5 units available", () => {
    const osrheTracks = Object.values(TRACK_CREDIT_MAP).filter((m) => m.osrheDashboard);
    expect(osrheTracks.length).toBeGreaterThanOrEqual(5);
  });
});
