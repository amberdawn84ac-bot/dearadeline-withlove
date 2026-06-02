#!/usr/bin/env node
/**
 * Hygraph Schema-as-Code Setup
 * Uses @hygraph/management-sdk to create all Adeline CMS models.
 *
 * NOTE: StudentProgress and LearningActivity are NOT in Hygraph — they are
 * transactional data stored in PostgreSQL (adeline-brain/prisma/schema.prisma).
 * Hygraph is for editorial/curatable content: lessons, blocks, projects.
 *
 * Run from the repo root on your LOCAL machine (Hygraph blocks cloud IPs):
 *
 *   npm install -D @hygraph/management-sdk   (once)
 *   node scripts/setup-hygraph.mjs
 *
 * Credentials are read from adeline-ui/.env.local automatically.
 * Idempotent-ish: re-running errors on existing models — that's safe to ignore.
 */

import { Client, SimpleFieldType, RelationalFieldType } from '@hygraph/management-sdk';
import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

// ── Load .env.local ───────────────────────────────────────────────────────────
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
  } catch { /* rely on process.env */ }
}

loadEnvLocal();

const HYGRAPH_ENDPOINT = process.env.HYGRAPH_ENDPOINT || '';
const HYGRAPH_TOKEN    = process.env.HYGRAPH_TOKEN    || '';

if (!HYGRAPH_ENDPOINT || !HYGRAPH_TOKEN) {
  console.error('❌ HYGRAPH_ENDPOINT and HYGRAPH_TOKEN are required.');
  console.error('   Set them in adeline-ui/.env.local or as environment variables.');
  process.exit(1);
}

// ── Enum definitions (match Prisma schema exactly) ────────────────────────────

const TRACK_VALUES = [
  { apiId: 'CREATION_SCIENCE',    displayName: 'Creation Science' },
  { apiId: 'HEALTH_NATUROPATHY',  displayName: 'Health & Naturopathy' },
  { apiId: 'HOMESTEADING',        displayName: 'Homesteading' },
  { apiId: 'GOVERNMENT_ECONOMICS',displayName: 'Government & Economics' },
  { apiId: 'JUSTICE_CHANGEMAKING',displayName: 'Justice & Changemaking' },
  { apiId: 'DISCIPLESHIP',        displayName: 'Discipleship' },
  { apiId: 'TRUTH_HISTORY',       displayName: 'Truth History' },
  { apiId: 'ENGLISH_LITERATURE',  displayName: 'English Literature' },
  { apiId: 'APPLIED_MATHEMATICS', displayName: 'Applied Mathematics' },
  { apiId: 'CREATIVE_ECONOMY',    displayName: 'Creative Economy' },
];

const DIFFICULTY_LEVEL_VALUES = [
  { apiId: 'EMERGING',   displayName: 'Emerging' },
  { apiId: 'DEVELOPING', displayName: 'Developing' },
  { apiId: 'EXPANDING',  displayName: 'Expanding' },
  { apiId: 'MASTERING',  displayName: 'Mastering' },
];

// 16 block types from Prisma schema
const BLOCK_TYPE_VALUES = [
  { apiId: 'TEXT',               displayName: 'Text' },
  { apiId: 'NARRATIVE',          displayName: 'Narrative' },
  { apiId: 'PRIMARY_SOURCE',     displayName: 'Primary Source' },
  { apiId: 'LAB_MISSION',        displayName: 'Lab Mission' },
  { apiId: 'EXPERIMENT',         displayName: 'Experiment' },
  { apiId: 'RESEARCH_MISSION',   displayName: 'Research Mission' },
  { apiId: 'QUIZ',               displayName: 'Quiz' },
  { apiId: 'DATA_TRACKING',      displayName: 'Data Tracking' },
  { apiId: 'PROBLEM',            displayName: 'Problem' },
  { apiId: 'WRITING',            displayName: 'Writing' },
  { apiId: 'SIMULATION',         displayName: 'Simulation' },
  { apiId: 'VIDEO',              displayName: 'Video' },
  { apiId: 'TEXT_DEEP',          displayName: 'Text Deep' },
  { apiId: 'REAL_WORLD_APP',     displayName: 'Real World Application' },
  { apiId: 'CORRECTIVE_OVERLAY', displayName: 'Corrective Overlay' },
  { apiId: 'CONCEPT_MAP',        displayName: 'Concept Map' },
];

const CREDIT_TYPE_VALUES = [
  { apiId: 'CORE',        displayName: 'Core' },
  { apiId: 'ELECTIVE',    displayName: 'Elective' },
  { apiId: 'PHYSICAL_ED', displayName: 'Physical Education' },
  { apiId: 'FINE_ARTS',   displayName: 'Fine Arts' },
  { apiId: 'HOMESTEAD',   displayName: 'Homestead' },
];

const GRADE_LETTER_VALUES = [
  { apiId: 'A_PLUS',     displayName: 'A+' },
  { apiId: 'A',          displayName: 'A' },
  { apiId: 'A_MINUS',    displayName: 'A-' },
  { apiId: 'B_PLUS',     displayName: 'B+' },
  { apiId: 'B',          displayName: 'B' },
  { apiId: 'B_MINUS',    displayName: 'B-' },
  { apiId: 'C_PLUS',     displayName: 'C+' },
  { apiId: 'C',          displayName: 'C' },
  { apiId: 'C_MINUS',    displayName: 'C-' },
  { apiId: 'D_PLUS',     displayName: 'D+' },
  { apiId: 'D',          displayName: 'D' },
  { apiId: 'D_MINUS',    displayName: 'D-' },
  { apiId: 'F',          displayName: 'F' },
  { apiId: 'PASS',       displayName: 'Pass' },
  { apiId: 'FAIL',       displayName: 'Fail' },
  { apiId: 'INCOMPLETE', displayName: 'Incomplete' },
];

const GRADE_BAND_VALUES = [
  { apiId: 'K2',         displayName: 'K-2' },
  { apiId: 'GRADES_3_5', displayName: '3-5' },
  { apiId: 'GRADES_6_8', displayName: '6-8' },
  { apiId: 'GRADES_9_12',displayName: '9-12' },
];

const SOURCE_TYPE_VALUES = [
  { apiId: 'ARCHIVE',   displayName: 'Archive' },
  { apiId: 'PRIMARY',   displayName: 'Primary Source' },
  { apiId: 'SECONDARY', displayName: 'Secondary Source' },
  { apiId: 'TOOL',      displayName: 'Tool' },
];

// ── Project category enum (for the Art/DIY + Farm project catalog) ────────────
const PROJECT_CATEGORY_VALUES = [
  { apiId: 'ART_CRAFT',    displayName: 'Art & Craft' },
  { apiId: 'DIY_BUILDING', displayName: 'DIY & Building' },
  { apiId: 'FARM_GARDEN',  displayName: 'Farm & Garden' },
  { apiId: 'COOKING_FOOD', displayName: 'Cooking & Food' },
  { apiId: 'SCIENCE_LAB',  displayName: 'Science Lab' },
  { apiId: 'ENTREPRENEURSHIP', displayName: 'Entrepreneurship' },
];

async function main() {
  console.log('Hygraph endpoint:', HYGRAPH_ENDPOINT);
  console.log('Building schema migration...\n');

  const client = new Client({
    authToken: HYGRAPH_TOKEN,
    endpoint:  HYGRAPH_ENDPOINT,
    name:      `adeline-schema-${Date.now()}`,
  });

  // ── 1. Enumerations ───────────────────────────────────────────────────────────
  console.log('Creating enumerations...');
  client.createEnumeration({ apiId: 'Track',           displayName: 'Track',            values: TRACK_VALUES });
  client.createEnumeration({ apiId: 'DifficultyLevel', displayName: 'Difficulty Level', values: DIFFICULTY_LEVEL_VALUES });
  client.createEnumeration({ apiId: 'BlockType',       displayName: 'Block Type',       values: BLOCK_TYPE_VALUES });
  client.createEnumeration({ apiId: 'CreditType',      displayName: 'Credit Type',      values: CREDIT_TYPE_VALUES });
  client.createEnumeration({ apiId: 'GradeLetter',     displayName: 'Grade Letter',     values: GRADE_LETTER_VALUES });
  client.createEnumeration({ apiId: 'GradeBand',       displayName: 'Grade Band',       values: GRADE_BAND_VALUES });
  client.createEnumeration({ apiId: 'SourceType',      displayName: 'Source Type',      values: SOURCE_TYPE_VALUES });
  client.createEnumeration({ apiId: 'ProjectCategory', displayName: 'Project Category', values: PROJECT_CATEGORY_VALUES });

  // ── 2. Models ─────────────────────────────────────────────────────────────────
  console.log('Creating models...');

  client.createModel({ apiId: 'Lesson',         apiIdPlural: 'Lessons',         displayName: 'Lesson',          description: 'Canonical lesson metadata' });
  client.createModel({ apiId: 'LessonBlock',    apiIdPlural: 'LessonBlocks',    displayName: 'Lesson Block',    description: 'Individual content block within a lesson' });
  client.createModel({ apiId: 'Project',        apiIdPlural: 'Projects',        displayName: 'Project',         description: 'Art/DIY/Farm project in the sovereign lab catalog' });
  client.createModel({ apiId: 'TrackPage',      apiIdPlural: 'TrackPages',      displayName: 'Track Page',      description: 'Curriculum overview page per track' });
  client.createModel({ apiId: 'CurriculumUnit', apiIdPlural: 'CurriculumUnits', displayName: 'Curriculum Unit', description: 'Multi-lesson thematic unit within a track' });
  client.createModel({ apiId: 'LessonStub',     apiIdPlural: 'LessonStubs',     displayName: 'Lesson Stub',     description: 'Lightweight lesson listing metadata' });
  client.createModel({ apiId: 'DailyBread',     apiIdPlural: 'DailyBreads',     displayName: 'Daily Bread',     description: 'Daily devotional scripture content' });
  client.createModel({ apiId: 'ResourceLink',   apiIdPlural: 'ResourceLinks',   displayName: 'Resource Link',   description: 'Curated external link per track' });

  // ── 3. Lesson fields ──────────────────────────────────────────────────────────
  console.log('Adding Lesson fields...');
  client.createSimpleField({ parentApiId: 'Lesson', apiId: 'title',            displayName: 'Title',             type: SimpleFieldType.String,  isRequired: true, isTitle: true });
  client.createEnumerableField({ parentApiId: 'Lesson', apiId: 'track',        displayName: 'Track',             enumerationApiId: 'Track',      isRequired: true });
  client.createEnumerableField({ parentApiId: 'Lesson', apiId: 'gradeBand',    displayName: 'Grade Band',        enumerationApiId: 'GradeBand',  isRequired: true });
  client.createEnumerableField({ parentApiId: 'Lesson', apiId: 'difficulty',   displayName: 'Difficulty',        enumerationApiId: 'DifficultyLevel' });
  client.createSimpleField({ parentApiId: 'Lesson', apiId: 'topicSlug',        displayName: 'Topic Slug',        type: SimpleFieldType.String,  isRequired: true, isUnique: true });
  client.createSimpleField({ parentApiId: 'Lesson', apiId: 'estimatedMinutes', displayName: 'Estimated Minutes', type: SimpleFieldType.Int });
  client.createSimpleField({ parentApiId: 'Lesson', apiId: 'oasStandards',     displayName: 'OAS Standards',     type: SimpleFieldType.String,  isList: true });
  client.createSimpleField({ parentApiId: 'Lesson', apiId: 'isHomestead',      displayName: 'Is Homestead',      type: SimpleFieldType.Boolean });
  client.createSimpleField({ parentApiId: 'Lesson', apiId: 'summary',          displayName: 'Summary',           type: SimpleFieldType.Richtext });

  // ── 4. LessonBlock fields ─────────────────────────────────────────────────────
  console.log('Adding LessonBlock fields...');
  client.createSimpleField({ parentApiId: 'LessonBlock', apiId: 'title',             displayName: 'Title',              type: SimpleFieldType.String, isRequired: true, isTitle: true });
  client.createEnumerableField({ parentApiId: 'LessonBlock', apiId: 'blockType',     displayName: 'Block Type',         enumerationApiId: 'BlockType',      isRequired: true });
  client.createEnumerableField({ parentApiId: 'LessonBlock', apiId: 'track',         displayName: 'Track',              enumerationApiId: 'Track',          isRequired: true });
  client.createEnumerableField({ parentApiId: 'LessonBlock', apiId: 'difficulty',    displayName: 'Difficulty',         enumerationApiId: 'DifficultyLevel' });
  client.createSimpleField({ parentApiId: 'LessonBlock', apiId: 'content',           displayName: 'Content',            type: SimpleFieldType.Richtext });
  client.createSimpleField({ parentApiId: 'LessonBlock', apiId: 'order',             displayName: 'Order',              type: SimpleFieldType.Int });
  client.createSimpleField({ parentApiId: 'LessonBlock', apiId: 'tags',              displayName: 'Tags',               type: SimpleFieldType.String, isList: true });
  client.createSimpleField({ parentApiId: 'LessonBlock', apiId: 'homesteadEnabled',  displayName: 'Homestead Enabled',  type: SimpleFieldType.Boolean });
  client.createSimpleField({ parentApiId: 'LessonBlock', apiId: 'homesteadContent',  displayName: 'Homestead Content',  type: SimpleFieldType.Richtext });
  client.createSimpleField({ parentApiId: 'LessonBlock', apiId: 'sourceTitle',       displayName: 'Source Title',       type: SimpleFieldType.String });
  client.createSimpleField({ parentApiId: 'LessonBlock', apiId: 'sourceUrl',         displayName: 'Source URL',         type: SimpleFieldType.String });

  // ── 5. Project fields ─────────────────────────────────────────────────────────
  console.log('Adding Project fields...');
  client.createSimpleField({ parentApiId: 'Project', apiId: 'title',            displayName: 'Title',             type: SimpleFieldType.String,  isRequired: true, isTitle: true });
  client.createSimpleField({ parentApiId: 'Project', apiId: 'slug',             displayName: 'Slug',              type: SimpleFieldType.String,  isRequired: true, isUnique: true });
  client.createEnumerableField({ parentApiId: 'Project', apiId: 'track',        displayName: 'Track',             enumerationApiId: 'Track',      isRequired: true });
  client.createEnumerableField({ parentApiId: 'Project', apiId: 'category',     displayName: 'Category',          enumerationApiId: 'ProjectCategory', isRequired: true });
  client.createEnumerableField({ parentApiId: 'Project', apiId: 'gradeBand',    displayName: 'Grade Band',        enumerationApiId: 'GradeBand' });
  client.createSimpleField({ parentApiId: 'Project', apiId: 'description',      displayName: 'Description',       type: SimpleFieldType.Richtext });
  client.createSimpleField({ parentApiId: 'Project', apiId: 'materials',        displayName: 'Materials',         type: SimpleFieldType.String,  isList: true });
  client.createSimpleField({ parentApiId: 'Project', apiId: 'steps',            displayName: 'Steps',             type: SimpleFieldType.Richtext });
  client.createSimpleField({ parentApiId: 'Project', apiId: 'estimatedMinutes', displayName: 'Estimated Minutes', type: SimpleFieldType.Int });
  client.createSimpleField({ parentApiId: 'Project', apiId: 'isSovereignLab',   displayName: 'Is Sovereign Lab',  type: SimpleFieldType.Boolean });
  client.createSimpleField({ parentApiId: 'Project', apiId: 'coverImageUrl',    displayName: 'Cover Image URL',   type: SimpleFieldType.String });
  client.createSimpleField({ parentApiId: 'Project', apiId: 'creditType',       displayName: 'Credit Type Hint',  type: SimpleFieldType.String });

  // ── 6. TrackPage fields ───────────────────────────────────────────────────────
  console.log('Adding TrackPage fields...');
  client.createEnumerableField({ parentApiId: 'TrackPage', apiId: 'track',       displayName: 'Track',       enumerationApiId: 'Track', isRequired: true, isUnique: true });
  client.createSimpleField({ parentApiId: 'TrackPage', apiId: 'title',           displayName: 'Title',       type: SimpleFieldType.String,  isRequired: true, isTitle: true });
  client.createSimpleField({ parentApiId: 'TrackPage', apiId: 'tagline',         displayName: 'Tagline',     type: SimpleFieldType.String });
  client.createSimpleField({ parentApiId: 'TrackPage', apiId: 'description',     displayName: 'Description', type: SimpleFieldType.Richtext });
  client.createSimpleField({ parentApiId: 'TrackPage', apiId: 'heroImageUrl',    displayName: 'Hero Image URL', type: SimpleFieldType.String });

  // ── 7. CurriculumUnit fields ──────────────────────────────────────────────────
  console.log('Adding CurriculumUnit fields...');
  client.createSimpleField({ parentApiId: 'CurriculumUnit', apiId: 'title',       displayName: 'Title',      type: SimpleFieldType.String,  isRequired: true, isTitle: true });
  client.createEnumerableField({ parentApiId: 'CurriculumUnit', apiId: 'track',   displayName: 'Track',      enumerationApiId: 'Track',     isRequired: true });
  client.createEnumerableField({ parentApiId: 'CurriculumUnit', apiId: 'gradeBand', displayName: 'Grade Band', enumerationApiId: 'GradeBand', isRequired: true });
  client.createSimpleField({ parentApiId: 'CurriculumUnit', apiId: 'oasStandards', displayName: 'OAS Standards', type: SimpleFieldType.String, isList: true });

  // ── 8. LessonStub fields ──────────────────────────────────────────────────────
  console.log('Adding LessonStub fields...');
  client.createSimpleField({ parentApiId: 'LessonStub', apiId: 'title',            displayName: 'Title',             type: SimpleFieldType.String,  isRequired: true, isTitle: true });
  client.createEnumerableField({ parentApiId: 'LessonStub', apiId: 'track',        displayName: 'Track',             enumerationApiId: 'Track',     isRequired: true });
  client.createEnumerableField({ parentApiId: 'LessonStub', apiId: 'gradeBand',    displayName: 'Grade Band',        enumerationApiId: 'GradeBand', isRequired: true });
  client.createSimpleField({ parentApiId: 'LessonStub', apiId: 'slug',             displayName: 'Slug',              type: SimpleFieldType.String,  isRequired: true, isUnique: true });
  client.createSimpleField({ parentApiId: 'LessonStub', apiId: 'estimatedMinutes', displayName: 'Estimated Minutes', type: SimpleFieldType.Int });
  client.createSimpleField({ parentApiId: 'LessonStub', apiId: 'oasStandards',     displayName: 'OAS Standards',     type: SimpleFieldType.String,  isList: true });
  client.createSimpleField({ parentApiId: 'LessonStub', apiId: 'isHomestead',      displayName: 'Is Homestead',      type: SimpleFieldType.Boolean });

  // ── 9. DailyBread fields ──────────────────────────────────────────────────────
  console.log('Adding DailyBread fields...');
  client.createSimpleField({ parentApiId: 'DailyBread', apiId: 'date',       displayName: 'Date',       type: SimpleFieldType.Date,   isRequired: true, isUnique: true });
  client.createSimpleField({ parentApiId: 'DailyBread', apiId: 'scripture',  displayName: 'Scripture',  type: SimpleFieldType.String, isRequired: true });
  client.createSimpleField({ parentApiId: 'DailyBread', apiId: 'reference',  displayName: 'Reference',  type: SimpleFieldType.String, isRequired: true });
  client.createSimpleField({ parentApiId: 'DailyBread', apiId: 'reflection', displayName: 'Reflection', type: SimpleFieldType.Richtext });
  client.createEnumerableField({ parentApiId: 'DailyBread', apiId: 'track',  displayName: 'Track',      enumerationApiId: 'Track' });

  // ── 10. ResourceLink fields ───────────────────────────────────────────────────
  console.log('Adding ResourceLink fields...');
  client.createSimpleField({ parentApiId: 'ResourceLink', apiId: 'title',       displayName: 'Title',       type: SimpleFieldType.String, isRequired: true, isTitle: true });
  client.createSimpleField({ parentApiId: 'ResourceLink', apiId: 'url',         displayName: 'URL',         type: SimpleFieldType.String, isRequired: true });
  client.createSimpleField({ parentApiId: 'ResourceLink', apiId: 'description', displayName: 'Description', type: SimpleFieldType.String });
  client.createEnumerableField({ parentApiId: 'ResourceLink', apiId: 'track',      displayName: 'Track',       enumerationApiId: 'Track',      isRequired: true });
  client.createEnumerableField({ parentApiId: 'ResourceLink', apiId: 'sourceType', displayName: 'Source Type', enumerationApiId: 'SourceType', isRequired: true });

  // ── 11. Relations ─────────────────────────────────────────────────────────────
  console.log('Adding relations...');

  // Lesson (1) → (many) LessonBlock
  client.createRelationalField({
    parentApiId: 'Lesson',
    apiId: 'blocks',
    displayName: 'Blocks',
    type: RelationalFieldType.Relation,
    isList: true,
    reverseField: { modelApiId: 'LessonBlock', apiId: 'lesson', displayName: 'Lesson', isList: false },
  });

  // TrackPage (1) → (many) CurriculumUnit
  client.createRelationalField({
    parentApiId: 'TrackPage',
    apiId: 'units',
    displayName: 'Units',
    type: RelationalFieldType.Relation,
    isList: true,
    reverseField: { modelApiId: 'CurriculumUnit', apiId: 'trackPage', displayName: 'Track Page', isList: false },
  });

  // CurriculumUnit (1) → (many) LessonStub
  client.createRelationalField({
    parentApiId: 'CurriculumUnit',
    apiId: 'lessonStubs',
    displayName: 'Lesson Stubs',
    type: RelationalFieldType.Relation,
    isList: true,
    reverseField: { modelApiId: 'LessonStub', apiId: 'unit', displayName: 'Unit', isList: false },
  });

  // ── Run ──────────────────────────────────────────────────────────────────────
  console.log('\nRunning migration against Hygraph (this may take 30–60 seconds)...\n');
  const result = await client.run(true);

  const here = dirname(fileURLToPath(import.meta.url));
  writeFileSync(join(here, 'hygraph-result.json'), JSON.stringify(result, null, 2));

  if (result.errors) {
    console.error('❌ Migration completed with errors. See scripts/hygraph-result.json');
    console.error('Summary:', JSON.stringify(result.errors).slice(0, 600));
    process.exit(1);
  }

  console.log('✅ Schema migration complete!');
  console.log('\nModels created:');
  console.log('  • Lesson        (with 9 fields + blocks relation)');
  console.log('  • LessonBlock   (with 11 fields)');
  console.log('  • Project       (with 12 fields)');
  console.log('  • TrackPage     (with 5 fields + units relation)');
  console.log('  • CurriculumUnit(with 4 fields + lessonStubs relation)');
  console.log('  • LessonStub    (with 7 fields)');
  console.log('  • DailyBread    (with 5 fields)');
  console.log('  • ResourceLink  (with 5 fields)');
  console.log('\nEnumerations: Track, DifficultyLevel, BlockType, CreditType, GradeLetter, GradeBand, SourceType, ProjectCategory');
  console.log('\nNote: StudentProgress and LearningActivity live in PostgreSQL (Prisma) — not Hygraph.');
  console.log('\nNext: Open Hygraph Studio → Schema to verify, then start adding content.');
}

main().catch((err) => {
  const here = dirname(fileURLToPath(import.meta.url));
  const details = { message: err?.message, name: err?.name, response: err?.response, errors: err?.errors, stack: err?.stack };
  try { writeFileSync(join(here, 'hygraph-result.json'), JSON.stringify(details, null, 2)); } catch {}
  console.error('\n❌ Error written to scripts/hygraph-result.json');
  console.error((err?.message || String(err)).slice(0, 400));
  process.exit(1);
});
