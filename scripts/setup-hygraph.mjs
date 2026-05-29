#!/usr/bin/env node
/**
 * Hygraph Schema-as-Code Setup
 * Uses the official @hygraph/management-sdk to create all Adeline CMS models.
 *
 * Install once:
 *   npm install -D @hygraph/management-sdk
 *
 * Run:
 *   $env:HYGRAPH_ENDPOINT="https://api-us-west-2.hygraph.com/v2/<project>/master"
 *   $env:HYGRAPH_TOKEN="<permanent-auth-token>"
 *   node scripts/setup-hygraph.mjs
 *
 * Idempotent-ish: re-running may error on existing components. To start clean,
 * delete the models in Hygraph Studio first, or comment out steps already done.
 */

import { Client, SimpleFieldType, RelationalFieldType } from '@hygraph/management-sdk';
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

// Load .env.local from adeline-ui if env vars aren't already set
function loadEnvLocal() {
  const here = dirname(fileURLToPath(import.meta.url));
  const envPath = join(here, '..', 'adeline-ui', '.env.local');
  try {
    const content = readFileSync(envPath, 'utf8');
    for (const line of content.split(/\r?\n/)) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith('#')) continue;
      const eq = trimmed.indexOf('=');
      if (eq === -1) continue;
      const key = trimmed.slice(0, eq).trim();
      const val = trimmed.slice(eq + 1).trim();
      if (!process.env[key]) process.env[key] = val;
    }
  } catch {
    // .env.local not found — rely on process.env
  }
}

loadEnvLocal();

const HYGRAPH_ENDPOINT = process.env.HYGRAPH_ENDPOINT || '';
const HYGRAPH_TOKEN = process.env.HYGRAPH_TOKEN || '';

if (!HYGRAPH_ENDPOINT || !HYGRAPH_TOKEN) {
  console.error('Error: HYGRAPH_ENDPOINT and HYGRAPH_TOKEN environment variables are required.');
  console.error('  $env:HYGRAPH_ENDPOINT="https://api-us-west-2.hygraph.com/v2/<project>/master"');
  console.error('  $env:HYGRAPH_TOKEN="<permanent-auth-token>"');
  process.exit(1);
}

// ── Enumeration values ───────────────────────────────────────────────────────
const TRACK_VALUES = [
  { apiId: 'CREATION_SCIENCE', displayName: 'Creation Science' },
  { apiId: 'HEALTH_NATUROPATHY', displayName: 'Health & Naturopathy' },
  { apiId: 'HOMESTEADING', displayName: 'Homesteading' },
  { apiId: 'GOVERNMENT_ECONOMICS', displayName: 'Government & Economics' },
  { apiId: 'JUSTICE_CHANGEMAKING', displayName: 'Justice & Changemaking' },
  { apiId: 'DISCIPLESHIP', displayName: 'Discipleship' },
  { apiId: 'TRUTH_HISTORY', displayName: 'Truth History' },
  { apiId: 'ENGLISH_LITERATURE', displayName: 'English Literature' },
  { apiId: 'APPLIED_MATHEMATICS', displayName: 'Applied Mathematics' },
  { apiId: 'CREATIVE_ECONOMY', displayName: 'Creative Economy' },
];

const GRADE_BAND_VALUES = [
  { apiId: 'K2', displayName: 'K-2' },
  { apiId: 'GRADES_3_5', displayName: '3-5' },
  { apiId: 'GRADES_6_8', displayName: '6-8' },
  { apiId: 'GRADES_9_12', displayName: '9-12' },
];

const SOURCE_TYPE_VALUES = [
  { apiId: 'ARCHIVE', displayName: 'Archive' },
  { apiId: 'PRIMARY', displayName: 'Primary Source' },
  { apiId: 'SECONDARY', displayName: 'Secondary Source' },
  { apiId: 'TOOL', displayName: 'Tool' },
];

async function main() {
  console.log('Content API:', HYGRAPH_ENDPOINT);
  console.log('Building migration...\n');

  const client = new Client({
    authToken: HYGRAPH_TOKEN,
    endpoint: HYGRAPH_ENDPOINT,
    name: `adeline-schema-${Date.now()}`, // must be unique per run
  });

  // ── 1. Enumerations ─────────────────────────────────────────────────────────
  client.createEnumeration({
    apiId: 'Track',
    displayName: 'Track',
    values: TRACK_VALUES,
  });

  client.createEnumeration({
    apiId: 'GradeBand',
    displayName: 'Grade Band',
    values: GRADE_BAND_VALUES,
  });

  client.createEnumeration({
    apiId: 'SourceType',
    displayName: 'Source Type',
    values: SOURCE_TYPE_VALUES,
  });

  // ── 2. Models ─────────────────────────────────────────────────────────────────
  client.createModel({
    apiId: 'TrackPage',
    apiIdPlural: 'TrackPages',
    displayName: 'Track Page',
    description: 'Curriculum overview page for each track',
  });

  client.createModel({
    apiId: 'CurriculumUnit',
    apiIdPlural: 'CurriculumUnits',
    displayName: 'Curriculum Unit',
    description: 'Multi-lesson thematic unit within a track',
  });

  client.createModel({
    apiId: 'LessonStub',
    apiIdPlural: 'LessonStubs',
    displayName: 'Lesson Stub',
    description: 'Lightweight lesson metadata',
  });

  client.createModel({
    apiId: 'DailyBread',
    apiIdPlural: 'DailyBreads',
    displayName: 'Daily Bread',
    description: 'Daily devotional scripture content',
  });

  client.createModel({
    apiId: 'ResourceLink',
    apiIdPlural: 'ResourceLinks',
    displayName: 'Resource Link',
    description: 'Curated external link for tracks',
  });

  // ── 3. TrackPage fields ───────────────────────────────────────────────────────
  client.createEnumerableField({
    parentApiId: 'TrackPage',
    apiId: 'track',
    displayName: 'Track',
    enumerationApiId: 'Track',
    isRequired: true,
    isUnique: true,
  });
  client.createSimpleField({
    parentApiId: 'TrackPage',
    apiId: 'title',
    displayName: 'Title',
    type: SimpleFieldType.String,
    isRequired: true,
    isTitle: true,
  });
  client.createSimpleField({
    parentApiId: 'TrackPage',
    apiId: 'tagline',
    displayName: 'Tagline',
    type: SimpleFieldType.String,
  });
  client.createSimpleField({
    parentApiId: 'TrackPage',
    apiId: 'description',
    displayName: 'Description',
    type: SimpleFieldType.Richtext,
  });
  client.createSimpleField({
    parentApiId: 'TrackPage',
    apiId: 'heroImageUrl',
    displayName: 'Hero Image URL',
    type: SimpleFieldType.String,
  });

  // ── 4. CurriculumUnit fields ──────────────────────────────────────────────────
  client.createEnumerableField({
    parentApiId: 'CurriculumUnit',
    apiId: 'track',
    displayName: 'Track',
    enumerationApiId: 'Track',
    isRequired: true,
  });
  client.createSimpleField({
    parentApiId: 'CurriculumUnit',
    apiId: 'title',
    displayName: 'Title',
    type: SimpleFieldType.String,
    isRequired: true,
    isTitle: true,
  });
  client.createEnumerableField({
    parentApiId: 'CurriculumUnit',
    apiId: 'gradeBand',
    displayName: 'Grade Band',
    enumerationApiId: 'GradeBand',
    isRequired: true,
  });
  client.createSimpleField({
    parentApiId: 'CurriculumUnit',
    apiId: 'oasStandards',
    displayName: 'OAS Standards',
    type: SimpleFieldType.String,
    isList: true,
  });

  // ── 5. LessonStub fields ──────────────────────────────────────────────────────
  client.createEnumerableField({
    parentApiId: 'LessonStub',
    apiId: 'track',
    displayName: 'Track',
    enumerationApiId: 'Track',
    isRequired: true,
  });
  client.createSimpleField({
    parentApiId: 'LessonStub',
    apiId: 'title',
    displayName: 'Title',
    type: SimpleFieldType.String,
    isRequired: true,
    isTitle: true,
  });
  client.createEnumerableField({
    parentApiId: 'LessonStub',
    apiId: 'gradeBand',
    displayName: 'Grade Band',
    enumerationApiId: 'GradeBand',
    isRequired: true,
  });
  client.createSimpleField({
    parentApiId: 'LessonStub',
    apiId: 'estimatedMinutes',
    displayName: 'Estimated Minutes',
    type: SimpleFieldType.Int,
  });
  client.createSimpleField({
    parentApiId: 'LessonStub',
    apiId: 'oasStandards',
    displayName: 'OAS Standards',
    type: SimpleFieldType.String,
    isList: true,
  });
  client.createSimpleField({
    parentApiId: 'LessonStub',
    apiId: 'isHomestead',
    displayName: 'Is Homestead',
    type: SimpleFieldType.Boolean,
  });
  client.createSimpleField({
    parentApiId: 'LessonStub',
    apiId: 'slug',
    displayName: 'Slug',
    type: SimpleFieldType.String,
    isRequired: true,
    isUnique: true,
  });

  // ── 6. DailyBread fields ──────────────────────────────────────────────────────
  client.createSimpleField({
    parentApiId: 'DailyBread',
    apiId: 'date',
    displayName: 'Date',
    type: SimpleFieldType.Date,
    isRequired: true,
    isUnique: true,
  });
  client.createSimpleField({
    parentApiId: 'DailyBread',
    apiId: 'scripture',
    displayName: 'Scripture',
    type: SimpleFieldType.String,
    isRequired: true,
  });
  client.createSimpleField({
    parentApiId: 'DailyBread',
    apiId: 'reference',
    displayName: 'Reference',
    type: SimpleFieldType.String,
    isRequired: true,
  });
  client.createSimpleField({
    parentApiId: 'DailyBread',
    apiId: 'reflection',
    displayName: 'Reflection',
    type: SimpleFieldType.Richtext,
  });
  client.createEnumerableField({
    parentApiId: 'DailyBread',
    apiId: 'track',
    displayName: 'Track',
    enumerationApiId: 'Track',
  });

  // ── 7. ResourceLink fields ────────────────────────────────────────────────────
  client.createEnumerableField({
    parentApiId: 'ResourceLink',
    apiId: 'track',
    displayName: 'Track',
    enumerationApiId: 'Track',
    isRequired: true,
  });
  client.createSimpleField({
    parentApiId: 'ResourceLink',
    apiId: 'title',
    displayName: 'Title',
    type: SimpleFieldType.String,
    isRequired: true,
    isTitle: true,
  });
  client.createSimpleField({
    parentApiId: 'ResourceLink',
    apiId: 'url',
    displayName: 'URL',
    type: SimpleFieldType.String,
    isRequired: true,
  });
  client.createSimpleField({
    parentApiId: 'ResourceLink',
    apiId: 'description',
    displayName: 'Description',
    type: SimpleFieldType.String,
  });
  client.createEnumerableField({
    parentApiId: 'ResourceLink',
    apiId: 'sourceType',
    displayName: 'Source Type',
    enumerationApiId: 'SourceType',
    isRequired: true,
  });

  // ── 8. Relations ──────────────────────────────────────────────────────────────
  // TrackPage (1) → (many) CurriculumUnit
  // Parent field is a list (TrackPage has many units); reverse is single.
  client.createRelationalField({
    parentApiId: 'TrackPage',
    apiId: 'units',
    displayName: 'Units',
    type: RelationalFieldType.Relation,
    isList: true,
    isRequired: false,
    reverseField: {
      modelApiId: 'CurriculumUnit',
      apiId: 'trackPage',
      displayName: 'Track Page',
      isList: false,
    },
  });

  // CurriculumUnit (1) → (many) LessonStub
  client.createRelationalField({
    parentApiId: 'CurriculumUnit',
    apiId: 'lessonStubs',
    displayName: 'Lesson Stubs',
    type: RelationalFieldType.Relation,
    isList: true,
    isRequired: false,
    reverseField: {
      modelApiId: 'LessonStub',
      apiId: 'unit',
      displayName: 'Unit',
      isList: false,
    },
  });

  // ── Run the migration ───────────────────────────────────────────────────────
  console.log('Running migration against Hygraph...\n');
  const result = await client.run(true); // true = foreground (wait for completion)

  // Write full result to a file for clean inspection (avoids terminal truncation)
  const here = dirname(fileURLToPath(import.meta.url));
  writeFileSync(join(here, 'hygraph-result.json'), JSON.stringify(result, null, 2));

  if (result.errors) {
    console.error('\n❌ Migration failed. Full result written to scripts/hygraph-result.json');
    console.error('Error summary:', typeof result.errors === 'string' ? result.errors : JSON.stringify(result.errors).slice(0, 500));
    process.exit(1);
  }

  console.log('✅ Schema migration complete!');
  console.log('\nNext steps:');
  console.log('1. Open Hygraph Studio → Schema to verify the 5 models');
  console.log('2. Content → TrackPage → Create an entry (e.g. CREATION_SCIENCE)');
  console.log('3. Restart your Next.js dev server and load the curriculum page');
}

main().catch((err) => {
  const here = dirname(fileURLToPath(import.meta.url));
  const details = {
    message: err?.message,
    name: err?.name,
    response: err?.response,
    errors: err?.errors,
    raw: String(err),
    stack: err?.stack,
  };
  try {
    writeFileSync(join(here, 'hygraph-result.json'), JSON.stringify(details, null, 2));
  } catch {}
  console.error('\n❌ Error written to scripts/hygraph-result.json');
  console.error((err?.message || String(err)).slice(0, 400));
  process.exit(1);
});
