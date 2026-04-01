import { describe, it, expect } from "vitest";
import {
  StandardsTagSchema,
  LearningEvidenceSchema,
  CreditBucket,
  StandardsFramework,
  StandardsSubject,
} from "../schemas/standards";

describe("StandardsTagSchema", () => {
  it("accepts a valid OAS tag", () => {
    const result = StandardsTagSchema.safeParse({
      framework: "OAS",
      subject: "ELA",
      code: "OK-ELA-8.R.1",
      weight: 0.8,
    });
    expect(result.success).toBe(true);
  });

  it("accepts a tag without code (code is optional)", () => {
    const result = StandardsTagSchema.safeParse({
      framework: "LOCAL",
      subject: "SCIENCE",
      weight: 0.5,
    });
    expect(result.success).toBe(true);
  });

  it("rejects weight outside 0–1", () => {
    const result = StandardsTagSchema.safeParse({
      framework: "OAS",
      subject: "MATH",
      weight: 1.5,
    });
    expect(result.success).toBe(false);
  });

  it("rejects unknown framework", () => {
    const result = StandardsTagSchema.safeParse({
      framework: "NGSS",
      subject: "SCIENCE",
      weight: 0.7,
    });
    expect(result.success).toBe(false);
  });
});

describe("CreditBucket enum", () => {
  it("has all 9 required buckets", () => {
    const buckets = Object.values(CreditBucket);
    expect(buckets).toContain("ENGLISH");
    expect(buckets).toContain("MATH");
    expect(buckets).toContain("LAB_SCIENCE");
    expect(buckets).toContain("SOCIAL_STUDIES");
    expect(buckets).toContain("HEALTH");
    expect(buckets).toContain("WORLD_LANGUAGE");
    expect(buckets).toContain("FINE_ARTS");
    expect(buckets).toContain("ELECTIVE");
    expect(buckets).toContain("PFL");
  });
});

describe("LearningEvidenceSchema", () => {
  it("accepts a valid lab evidence entry", () => {
    const result = LearningEvidenceSchema.safeParse({
      artifactType: "lab",
      masteryScore: 0.92,
      hours: 2.5,
    });
    expect(result.success).toBe(true);
  });

  it("rejects masteryScore > 1", () => {
    const result = LearningEvidenceSchema.safeParse({
      artifactType: "essay",
      masteryScore: 1.1,
      hours: 3,
    });
    expect(result.success).toBe(false);
  });

  it("rejects unknown artifactType", () => {
    const result = LearningEvidenceSchema.safeParse({
      artifactType: "homework",
      masteryScore: 0.8,
      hours: 1,
    });
    expect(result.success).toBe(false);
  });

  it("rejects negative hours", () => {
    const result = LearningEvidenceSchema.safeParse({
      artifactType: "quiz",
      masteryScore: 0.75,
      hours: -1,
    });
    expect(result.success).toBe(false);
  });
});
