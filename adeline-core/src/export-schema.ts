/**
 * Schema Bridge — exports JSON Schema for adeline-brain (Python/Pydantic).
 * Run: npx ts-node src/export-schema.ts > ../adeline-brain/app/schemas/core_schema.json
 *
 * adeline-brain's Pydantic models are validated against this output in CI
 * to ensure the Python layer stays in sync with the TypeScript source of truth.
 */
import { zodToJsonSchema } from "zod-to-json-schema";
import { EvidenceSchema, UserSchema, LessonBlockSchema, LessonSchema } from "./types";

const bridge = {
  $schema: "http://json-schema.org/draft-07/schema#",
  title: "adeline-core Bridge Schema",
  description: "Generated from Zod — do not edit manually. Re-run export-schema.ts to update.",
  definitions: {
    Evidence:    zodToJsonSchema(EvidenceSchema,    { name: "Evidence" }),
    User:        zodToJsonSchema(UserSchema,        { name: "User" }),
    LessonBlock: zodToJsonSchema(LessonBlockSchema, { name: "LessonBlock" }),
    Lesson:      zodToJsonSchema(LessonSchema,      { name: "Lesson" }),
  },
};

console.log(JSON.stringify(bridge, null, 2));
