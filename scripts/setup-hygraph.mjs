#!/usr/bin/env node
/**
 * Hygraph Schema-as-Code Setup — idempotent
 *
 * Introspects the live schema first, then only creates what's missing.
 * Safe to re-run after partial failures.
 *
 * Run from the repo root on your LOCAL machine:
 *   node scripts/setup-hygraph.mjs
 *
 * Credentials auto-loaded from adeline-ui/.env.local
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
  console.error('   Set them in adeline-ui/.env.local');
  process.exit(1);
}

// ── Introspect existing schema ────────────────────────────────────────────────
async function getExistingSchema() {
  const res = await fetch(HYGRAPH_ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${HYGRAPH_TOKEN}` },
    body: JSON.stringify({ query: '{ __schema { types { name kind } } }' }),
  });
  const json = await res.json();
  const types = json?.data?.__schema?.types ?? [];
  const existing = new Set(types.map(t => t.name));
  return existing;
}

// ── Enum definitions ──────────────────────────────────────────────────────────

const ENUMERATIONS = [
  {
    apiId: 'Track', displayName: 'Track',
    values: [
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
    ],
  },
  {
    apiId: 'DifficultyLevel', displayName: 'Difficulty Level',
    values: [
      { apiId: 'EMERGING',   displayName: 'Emerging' },
      { apiId: 'DEVELOPING', displayName: 'Developing' },
      { apiId: 'EXPANDING',  displayName: 'Expanding' },
      { apiId: 'MASTERING',  displayName: 'Mastering' },
    ],
  },
  {
    apiId: 'BlockType', displayName: 'Block Type',
    values: [
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
    ],
  },
  {
    apiId: 'CreditType', displayName: 'Credit Type',
    values: [
      { apiId: 'CORE',        displayName: 'Core' },
      { apiId: 'ELECTIVE',    displayName: 'Elective' },
      { apiId: 'PHYSICAL_ED', displayName: 'Physical Education' },
      { apiId: 'FINE_ARTS',   displayName: 'Fine Arts' },
      { apiId: 'HOMESTEAD',   displayName: 'Homestead' },
    ],
  },
  {
    apiId: 'GradeLetter', displayName: 'Grade Letter',
    values: [
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
    ],
  },
  {
    apiId: 'GradeBand', displayName: 'Grade Band',
    values: [
      { apiId: 'K2',          displayName: 'K-2' },
      { apiId: 'GRADES_3_5',  displayName: '3-5' },
      { apiId: 'GRADES_6_8',  displayName: '6-8' },
      { apiId: 'GRADES_9_12', displayName: '9-12' },
    ],
  },
  {
    apiId: 'SourceType', displayName: 'Source Type',
    values: [
      { apiId: 'ARCHIVE',   displayName: 'Archive' },
      { apiId: 'PRIMARY',   displayName: 'Primary Source' },
      { apiId: 'SECONDARY', displayName: 'Secondary Source' },
      { apiId: 'TOOL',      displayName: 'Tool' },
    ],
  },
  {
    apiId: 'ProjectCategory', displayName: 'Project Category',
    values: [
      { apiId: 'ART_CRAFT',        displayName: 'Art & Craft' },
      { apiId: 'DIY_BUILDING',     displayName: 'DIY & Building' },
      { apiId: 'FARM_GARDEN',      displayName: 'Farm & Garden' },
      { apiId: 'COOKING_FOOD',     displayName: 'Cooking & Food' },
      { apiId: 'SCIENCE_LAB',      displayName: 'Science Lab' },
      { apiId: 'ENTREPRENEURSHIP', displayName: 'Entrepreneurship' },
    ],
  },
];

// Models and their fields
const MODELS = [
  { apiId: 'Lesson',         apiIdPlural: 'Lessons',         displayName: 'Lesson',           description: 'Canonical lesson metadata' },
  { apiId: 'LessonBlock',    apiIdPlural: 'LessonBlocks',    displayName: 'Lesson Block',      description: 'Individual content block within a lesson' },
  { apiId: 'Project',        apiIdPlural: 'Projects',        displayName: 'Project',           description: 'Art/DIY/Farm project in the sovereign lab catalog' },
  { apiId: 'TrackPage',      apiIdPlural: 'TrackPages',      displayName: 'Track Page',        description: 'Curriculum overview page per track' },
  { apiId: 'CurriculumUnit', apiIdPlural: 'CurriculumUnits', displayName: 'Curriculum Unit',   description: 'Multi-lesson thematic unit within a track' },
  { apiId: 'LessonStub',     apiIdPlural: 'LessonStubs',     displayName: 'Lesson Stub',       description: 'Lightweight lesson listing metadata' },
  { apiId: 'DailyBread',     apiIdPlural: 'DailyBreads',     displayName: 'Daily Bread',       description: 'Daily devotional scripture content' },
  { apiId: 'ResourceLink',   apiIdPlural: 'ResourceLinks',   displayName: 'Resource Link',     description: 'Curated external link per track' },
];

async function main() {
  console.log('Endpoint:', HYGRAPH_ENDPOINT);

  // ── Introspect what already exists ──────────────────────────────────────────
  console.log('\nIntrospecting existing schema...');
  const existing = await getExistingSchema();
  console.log(`Found ${existing.size} existing types.\n`);

  const client = new Client({
    authToken: HYGRAPH_TOKEN,
    endpoint:  HYGRAPH_ENDPOINT,
    name:      `adeline-schema-${Date.now()}`,
  });

  let enumsSkipped   = 0;
  let enumsQueued    = 0;
  let modelsSkipped  = 0;
  let modelsQueued   = 0;

  // ── Enumerations (skip if already present) ──────────────────────────────────
  for (const enumDef of ENUMERATIONS) {
    if (existing.has(enumDef.apiId)) {
      console.log(`  ⏭  Enum ${enumDef.apiId} already exists — skipping`);
      enumsSkipped++;
    } else {
      console.log(`  ✚  Enum ${enumDef.apiId} — queuing create`);
      client.createEnumeration(enumDef);
      enumsQueued++;
    }
  }

  // ── Models (skip if already present) ───────────────────────────────────────
  for (const model of MODELS) {
    if (existing.has(model.apiId)) {
      console.log(`  ⏭  Model ${model.apiId} already exists — skipping`);
      modelsSkipped++;
    } else {
      console.log(`  ✚  Model ${model.apiId} — queuing create`);
      client.createModel(model);
      modelsQueued++;
    }
  }

  // ── Fields — always attempt; SDK errors on duplicates but that's OK ─────────
  // We track which models exist to know whether to add fields.
  // If a model was just queued for creation, fields must be added too.
  // If it already existed, its fields likely exist — but adding them
  // will just produce per-field errors in the result (non-fatal for our purposes).

  const needsFields = new Set(MODELS.map(m => m.apiId)); // add fields for all

  if (needsFields.has('Lesson')) {
    client.createSimpleField({ parentApiId: 'Lesson', apiId: 'title',            displayName: 'Title',             type: SimpleFieldType.String,  isRequired: true, isTitle: true });
    client.createEnumerableField({ parentApiId: 'Lesson', apiId: 'track',        displayName: 'Track',             enumerationApiId: 'Track',     isRequired: true });
    client.createEnumerableField({ parentApiId: 'Lesson', apiId: 'gradeBand',    displayName: 'Grade Band',        enumerationApiId: 'GradeBand', isRequired: true });
    client.createEnumerableField({ parentApiId: 'Lesson', apiId: 'difficulty',   displayName: 'Difficulty',        enumerationApiId: 'DifficultyLevel' });
    client.createSimpleField({ parentApiId: 'Lesson', apiId: 'topicSlug',        displayName: 'Topic Slug',        type: SimpleFieldType.String,  isRequired: true, isUnique: true });
    client.createSimpleField({ parentApiId: 'Lesson', apiId: 'estimatedMinutes', displayName: 'Estimated Minutes', type: SimpleFieldType.Int });
    client.createSimpleField({ parentApiId: 'Lesson', apiId: 'oasStandards',     displayName: 'OAS Standards',     type: SimpleFieldType.String,  isList: true });
    client.createSimpleField({ parentApiId: 'Lesson', apiId: 'isHomestead',      displayName: 'Is Homestead',      type: SimpleFieldType.Boolean });
    client.createSimpleField({ parentApiId: 'Lesson', apiId: 'summary',          displayName: 'Summary',           type: SimpleFieldType.Richtext });
  }

  if (needsFields.has('LessonBlock')) {
    client.createSimpleField({ parentApiId: 'LessonBlock', apiId: 'title',            displayName: 'Title',             type: SimpleFieldType.String,  isRequired: true, isTitle: true });
    client.createEnumerableField({ parentApiId: 'LessonBlock', apiId: 'blockType',    displayName: 'Block Type',        enumerationApiId: 'BlockType', isRequired: true });
    client.createEnumerableField({ parentApiId: 'LessonBlock', apiId: 'track',        displayName: 'Track',             enumerationApiId: 'Track',     isRequired: true });
    client.createEnumerableField({ parentApiId: 'LessonBlock', apiId: 'difficulty',   displayName: 'Difficulty',        enumerationApiId: 'DifficultyLevel' });
    client.createSimpleField({ parentApiId: 'LessonBlock', apiId: 'content',          displayName: 'Content',           type: SimpleFieldType.Richtext });
    client.createSimpleField({ parentApiId: 'LessonBlock', apiId: 'order',            displayName: 'Order',             type: SimpleFieldType.Int });
    client.createSimpleField({ parentApiId: 'LessonBlock', apiId: 'tags',             displayName: 'Tags',              type: SimpleFieldType.String,  isList: true });
    client.createSimpleField({ parentApiId: 'LessonBlock', apiId: 'homesteadEnabled', displayName: 'Homestead Enabled', type: SimpleFieldType.Boolean });
    client.createSimpleField({ parentApiId: 'LessonBlock', apiId: 'homesteadContent', displayName: 'Homestead Content', type: SimpleFieldType.Richtext });
    client.createSimpleField({ parentApiId: 'LessonBlock', apiId: 'sourceTitle',      displayName: 'Source Title',      type: SimpleFieldType.String });
    client.createSimpleField({ parentApiId: 'LessonBlock', apiId: 'sourceUrl',        displayName: 'Source URL',        type: SimpleFieldType.String });
  }

  if (needsFields.has('Project')) {
    client.createSimpleField({ parentApiId: 'Project', apiId: 'title',            displayName: 'Title',             type: SimpleFieldType.String,  isRequired: true, isTitle: true });
    client.createSimpleField({ parentApiId: 'Project', apiId: 'slug',             displayName: 'Slug',              type: SimpleFieldType.String,  isRequired: true, isUnique: true });
    client.createEnumerableField({ parentApiId: 'Project', apiId: 'track',        displayName: 'Track',             enumerationApiId: 'Track',           isRequired: true });
    client.createEnumerableField({ parentApiId: 'Project', apiId: 'category',     displayName: 'Category',          enumerationApiId: 'ProjectCategory', isRequired: true });
    client.createEnumerableField({ parentApiId: 'Project', apiId: 'gradeBand',    displayName: 'Grade Band',        enumerationApiId: 'GradeBand' });
    client.createSimpleField({ parentApiId: 'Project', apiId: 'description',      displayName: 'Description',       type: SimpleFieldType.Richtext });
    client.createSimpleField({ parentApiId: 'Project', apiId: 'materials',        displayName: 'Materials',         type: SimpleFieldType.String,  isList: true });
    client.createSimpleField({ parentApiId: 'Project', apiId: 'steps',            displayName: 'Steps',             type: SimpleFieldType.Richtext });
    client.createSimpleField({ parentApiId: 'Project', apiId: 'estimatedMinutes', displayName: 'Estimated Minutes', type: SimpleFieldType.Int });
    client.createSimpleField({ parentApiId: 'Project', apiId: 'isSovereignLab',   displayName: 'Is Sovereign Lab',  type: SimpleFieldType.Boolean });
    client.createSimpleField({ parentApiId: 'Project', apiId: 'coverImageUrl',    displayName: 'Cover Image URL',   type: SimpleFieldType.String });
  }

  if (needsFields.has('TrackPage')) {
    client.createEnumerableField({ parentApiId: 'TrackPage', apiId: 'track',       displayName: 'Track',        enumerationApiId: 'Track', isRequired: true, isUnique: true });
    client.createSimpleField({ parentApiId: 'TrackPage', apiId: 'title',           displayName: 'Title',        type: SimpleFieldType.String,  isRequired: true, isTitle: true });
    client.createSimpleField({ parentApiId: 'TrackPage', apiId: 'tagline',         displayName: 'Tagline',      type: SimpleFieldType.String });
    client.createSimpleField({ parentApiId: 'TrackPage', apiId: 'description',     displayName: 'Description',  type: SimpleFieldType.Richtext });
    client.createSimpleField({ parentApiId: 'TrackPage', apiId: 'heroImageUrl',    displayName: 'Hero Image URL', type: SimpleFieldType.String });
  }

  if (needsFields.has('CurriculumUnit')) {
    client.createSimpleField({ parentApiId: 'CurriculumUnit', apiId: 'title',         displayName: 'Title',      type: SimpleFieldType.String,  isRequired: true, isTitle: true });
    client.createEnumerableField({ parentApiId: 'CurriculumUnit', apiId: 'track',     displayName: 'Track',      enumerationApiId: 'Track',     isRequired: true });
    client.createEnumerableField({ parentApiId: 'CurriculumUnit', apiId: 'gradeBand', displayName: 'Grade Band', enumerationApiId: 'GradeBand', isRequired: true });
    client.createSimpleField({ parentApiId: 'CurriculumUnit', apiId: 'oasStandards', displayName: 'OAS Standards', type: SimpleFieldType.String, isList: true });
  }

  if (needsFields.has('LessonStub')) {
    client.createSimpleField({ parentApiId: 'LessonStub', apiId: 'title',            displayName: 'Title',             type: SimpleFieldType.String,  isRequired: true, isTitle: true });
    client.createEnumerableField({ parentApiId: 'LessonStub', apiId: 'track',        displayName: 'Track',             enumerationApiId: 'Track',     isRequired: true });
    client.createEnumerableField({ parentApiId: 'LessonStub', apiId: 'gradeBand',    displayName: 'Grade Band',        enumerationApiId: 'GradeBand', isRequired: true });
    client.createSimpleField({ parentApiId: 'LessonStub', apiId: 'slug',             displayName: 'Slug',              type: SimpleFieldType.String,  isRequired: true, isUnique: true });
    client.createSimpleField({ parentApiId: 'LessonStub', apiId: 'estimatedMinutes', displayName: 'Estimated Minutes', type: SimpleFieldType.Int });
    client.createSimpleField({ parentApiId: 'LessonStub', apiId: 'oasStandards',     displayName: 'OAS Standards',     type: SimpleFieldType.String,  isList: true });
    client.createSimpleField({ parentApiId: 'LessonStub', apiId: 'isHomestead',      displayName: 'Is Homestead',      type: SimpleFieldType.Boolean });
  }

  if (needsFields.has('DailyBread')) {
    client.createSimpleField({ parentApiId: 'DailyBread', apiId: 'date',       displayName: 'Date',       type: SimpleFieldType.Date,   isRequired: true, isUnique: true });
    client.createSimpleField({ parentApiId: 'DailyBread', apiId: 'scripture',  displayName: 'Scripture',  type: SimpleFieldType.String, isRequired: true });
    client.createSimpleField({ parentApiId: 'DailyBread', apiId: 'reference',  displayName: 'Reference',  type: SimpleFieldType.String, isRequired: true });
    client.createSimpleField({ parentApiId: 'DailyBread', apiId: 'reflection', displayName: 'Reflection', type: SimpleFieldType.Richtext });
    client.createEnumerableField({ parentApiId: 'DailyBread', apiId: 'track',  displayName: 'Track',      enumerationApiId: 'Track' });
  }

  if (needsFields.has('ResourceLink')) {
    client.createSimpleField({ parentApiId: 'ResourceLink', apiId: 'title',       displayName: 'Title',       type: SimpleFieldType.String, isRequired: true, isTitle: true });
    client.createSimpleField({ parentApiId: 'ResourceLink', apiId: 'url',         displayName: 'URL',         type: SimpleFieldType.String, isRequired: true });
    client.createSimpleField({ parentApiId: 'ResourceLink', apiId: 'description', displayName: 'Description', type: SimpleFieldType.String });
    client.createEnumerableField({ parentApiId: 'ResourceLink', apiId: 'track',      displayName: 'Track',       enumerationApiId: 'Track',      isRequired: true });
    client.createEnumerableField({ parentApiId: 'ResourceLink', apiId: 'sourceType', displayName: 'Source Type', enumerationApiId: 'SourceType', isRequired: true });
  }

  // ── Relations ───────────────────────────────────────────────────────────────
  client.createRelationalField({
    parentApiId: 'Lesson', apiId: 'blocks', displayName: 'Blocks',
    type: RelationalFieldType.Relation, isList: true,
    reverseField: { modelApiId: 'LessonBlock', apiId: 'lesson', displayName: 'Lesson', isList: false },
  });
  client.createRelationalField({
    parentApiId: 'TrackPage', apiId: 'units', displayName: 'Units',
    type: RelationalFieldType.Relation, isList: true,
    reverseField: { modelApiId: 'CurriculumUnit', apiId: 'trackPage', displayName: 'Track Page', isList: false },
  });
  client.createRelationalField({
    parentApiId: 'CurriculumUnit', apiId: 'lessonStubs', displayName: 'Lesson Stubs',
    type: RelationalFieldType.Relation, isList: true,
    reverseField: { modelApiId: 'LessonStub', apiId: 'unit', displayName: 'Unit', isList: false },
  });

  if (enumsQueued === 0 && modelsQueued === 0) {
    console.log('\n✅ All enums and models already exist — nothing to create.');
    console.log('   Field additions will still be attempted (duplicates are skipped by Hygraph).');
  }

  console.log(`\nQueued: ${enumsQueued} enums, ${modelsQueued} models (skipped ${enumsSkipped} enums, ${modelsSkipped} models)`);
  console.log('Running migration...\n');

  const result = await client.run(true);

  const here = dirname(fileURLToPath(import.meta.url));
  writeFileSync(join(here, 'hygraph-result.json'), JSON.stringify(result, null, 2));

  // Count errors — field-level "already exists" errors are non-fatal
  const errors = result?.errors;
  const hasHardErrors = errors && (
    typeof errors === 'string'
      ? !errors.includes('already')
      : JSON.stringify(errors).match(/"(?!.*already).*[Ee]rror/) !== null
  );

  if (hasHardErrors) {
    console.error('❌ Migration failed. See scripts/hygraph-result.json');
    console.error(JSON.stringify(errors).slice(0, 600));
    process.exit(1);
  }

  if (errors) {
    console.log('⚠️  Some operations were skipped (fields/relations already existed) — that\'s OK.');
  }

  console.log('✅ Schema migration complete!');
  console.log('\nModels in your Hygraph project:');
  console.log('  Lesson, LessonBlock, Project, TrackPage, CurriculumUnit, LessonStub, DailyBread, ResourceLink');
  console.log('\nOpen Hygraph Studio → Schema to verify, then start adding content.');
}

main().catch((err) => {
  const here = dirname(fileURLToPath(import.meta.url));
  try { writeFileSync(join(here, 'hygraph-result.json'), JSON.stringify({ message: err?.message, stack: err?.stack, raw: String(err) }, null, 2)); } catch {}
  console.error('\n❌ Error written to scripts/hygraph-result.json');
  console.error((err?.message || String(err)).slice(0, 400));
  process.exit(1);
});
