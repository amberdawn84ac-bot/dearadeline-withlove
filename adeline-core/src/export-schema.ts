/**
 * Schema Bridge — exports JSON Schema for adeline-brain (Python/Pydantic).
 * Run: npx ts-node src/export-schema.ts > ../adeline-brain/app/schemas/core_schema.json
 *
 * adeline-brain's Pydantic models are validated against this output in CI
 * to ensure the Python layer stays in sync with the TypeScript source of truth.
 */
import { z } from "zod";
import { EvidenceSchema, UserSchema, LessonBlockSchema, LessonSchema } from "./types";

const bridge = {
  $schema: "http://json-schema.org/draft-07/schema#",
  title: "adeline-core Bridge Schema",
  description: "Generated from Zod — do not edit manually. Re-run export-schema.ts to update.",
  definitions: {
    Evidence:    z.toJSONSchema(EvidenceSchema, { target: "draft-7", unrepresentable: "any" }),
    User:        z.toJSONSchema(UserSchema, { target: "draft-7", unrepresentable: "any" }),
    LessonBlock: z.toJSONSchema(LessonBlockSchema, { target: "draft-7", unrepresentable: "any" }),
    Lesson:      z.toJSONSchema(LessonSchema, { target: "draft-7", unrepresentable: "any" }),
  },
};

console.log(JSON.stringify(bridge, null, 2));
