#!/usr/bin/env node
/**
 * Hygraph Schema Setup Script
 * Creates all content models, enumerations, and fields for Adeline CMS
 *
 * Usage:
 *   node scripts/setup-hygraph.js
 *
 * Requires HYGRAPH_TOKEN and HYGRAPH_ENDPOINT in environment
 */

const HYGRAPH_ENDPOINT = process.env.HYGRAPH_ENDPOINT || '';
const HYGRAPH_TOKEN = process.env.HYGRAPH_TOKEN || '';

if (!HYGRAPH_ENDPOINT || !HYGRAPH_TOKEN) {
  console.error('Error: HYGRAPH_ENDPOINT and HYGRAPH_TOKEN required');
  console.error('Example:');
  console.error('  HYGRAPH_ENDPOINT=https://api-us-west-2.hygraph.com/v2/xxx/master');
  console.error('  HYGRAPH_TOKEN=eyJhbGci...');
  console.error('  node scripts/setup-hygraph.js');
  process.exit(1);
}

// Management API is at management-{region}.hygraph.com
// Content API: https://api-us-west-2.hygraph.com/v2/{project}/master
// Management API: https://management-us-west-2.hygraph.com/graphql
const MANAGEMENT_API = HYGRAPH_ENDPOINT
  .replace('api-', 'management-')
  .replace(/\/v2\/[^/]+\/master$/, '/graphql');

console.log('Content API:', HYGRAPH_ENDPOINT);
console.log('Management API:', MANAGEMENT_API);
console.log();

// GraphQL mutation helpers
async function managementQuery(query, variables = {}) {
  const response = await fetch(MANAGEMENT_API, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${HYGRAPH_TOKEN}`
    },
    body: JSON.stringify({ query, variables })
  });

  const data = await response.json();
  if (data.errors) {
    throw new Error(JSON.stringify(data.errors, null, 2));
  }
  return data.data;
}

// Create enumeration
async function createEnumeration(apiId, displayName, values) {
  const query = `
    mutation CreateEnumeration($input: CreateEnumerationInput!) {
      createEnumeration(data: $input) {
        __typename
      }
    }
  `;

  const input = {
    apiId,
    displayName,
    values: values.map(v => ({
      apiId: v.apiId,
      displayName: v.displayName
    }))
  };

  try {
    await managementQuery(query, { input });
    console.log(`✓ Created enum: ${apiId}`);
  } catch (err) {
    if (err.message.includes('already exists')) {
      console.log(`• Enum exists: ${apiId}`);
      return null;
    }
    throw err;
  }
}

// Create model
async function createModel(apiId, displayName, description = '') {
  const query = `
    mutation CreateModel($input: CreateModelInput!) {
      createModel(data: $input) {
        __typename
      }
    }
  `;

  const input = {
    apiId,
    apiIdPlural: apiId + 's',
    displayName,
    description
  };

  try {
    await managementQuery(query, { input });
    console.log(`✓ Created model: ${apiId}`);
  } catch (err) {
    if (err.message.includes('already exists')) {
      console.log(`• Model exists: ${apiId}`);
      return null;
    }
    throw err;
  }
}

// Create simple field
async function createSimpleField(parentApiId, apiId, type, displayName, options = {}) {
  const query = `
    mutation CreateSimpleField($input: CreateSimpleFieldInput!) {
      createSimpleField(data: $input) {
        __typename
      }
    }
  `;

  const input = {
    parentApiId,
    apiId,
    type,
    displayName,
    ...options
  };

  try {
    await managementQuery(query, { input });
    console.log(`  ✓ Field: ${apiId}`);
  } catch (err) {
    if (err.message.includes('already exists')) {
      console.log(`  • Field exists: ${apiId}`);
      return null;
    }
    throw err;
  }
}

// Create enumerable field
async function createEnumerableField(parentApiId, apiId, enumerationApiId, displayName, options = {}) {
  const query = `
    mutation CreateEnumerableField($input: CreateEnumerableFieldInput!) {
      createEnumerableField(data: $input) {
        __typename
      }
    }
  `;

  const input = {
    parentApiId,
    apiId,
    enumerationApiId,
    displayName,
    ...options
  };

  try {
    await managementQuery(query, { input });
    console.log(`  ✓ Enum field: ${apiId}`);
  } catch (err) {
    if (err.message.includes('already exists')) {
      console.log(`  • Enum field exists: ${apiId}`);
      return null;
    }
    throw err;
  }
}

// Create relational field
async function createRelationalField(parentApiId, apiId, targetModelApiId, displayName, isList = false) {
  const query = `
    mutation CreateRelationalField($input: CreateRelationalFieldInput!) {
      createRelationalField(data: $input) {
        __typename
      }
    }
  `;

  const input = {
    parentApiId,
    apiId,
    type: 'RELATION',
    displayName,
    isList,
    reverseField: {
      modelApiId: targetModelApiId,
      apiId: isList ? parentApiId.toLowerCase() + 's' : parentApiId.toLowerCase(),
      displayName: isList ? `${parentApiId}s` : parentApiId,
      isList: !isList
    }
  };

  try {
    await managementQuery(query, { input });
    console.log(`  ✓ Relation: ${apiId} → ${targetModelApiId}`);
  } catch (err) {
    if (err.message.includes('already exists')) {
      console.log(`  • Relation exists: ${apiId}`);
      return null;
    }
    throw err;
  }
}

// Main setup
async function main() {
  console.log('Setting up Hygraph schema...\n');

  // 1. Create enumerations
  console.log('Creating enumerations...');
  await createEnumeration('Track', 'Track', [
    { apiId: 'CREATION_SCIENCE', displayName: 'Creation Science' },
    { apiId: 'HEALTH_NATUROPATHY', displayName: 'Health & Naturopathy' },
    { apiId: 'HOMESTEADING', displayName: 'Homesteading' },
    { apiId: 'GOVERNMENT_ECONOMICS', displayName: 'Government & Economics' },
    { apiId: 'JUSTICE_CHANGEMAKING', displayName: 'Justice & Changemaking' },
    { apiId: 'DISCIPLESHIP', displayName: 'Discipleship' },
    { apiId: 'TRUTH_HISTORY', displayName: 'Truth History' },
    { apiId: 'ENGLISH_LITERATURE', displayName: 'English Literature' },
    { apiId: 'APPLIED_MATHEMATICS', displayName: 'Applied Mathematics' },
    { apiId: 'CREATIVE_ECONOMY', displayName: 'Creative Economy' }
  ]);

  await createEnumeration('GradeBand', 'Grade Band', [
    { apiId: 'K2', displayName: 'K-2' },
    { apiId: '3_5', displayName: '3-5' },
    { apiId: '6_8', displayName: '6-8' },
    { apiId: '9_12', displayName: '9-12' }
  ]);

  await createEnumeration('SourceType', 'Source Type', [
    { apiId: 'ARCHIVE', displayName: 'Archive' },
    { apiId: 'PRIMARY', displayName: 'Primary Source' },
    { apiId: 'SECONDARY', displayName: 'Secondary Source' },
    { apiId: 'TOOL', displayName: 'Tool' }
  ]);

  // 2. Create models
  console.log('\nCreating models...');
  await createModel('TrackPage', 'Track Page', 'Curriculum overview page for each track');
  await createModel('CurriculumUnit', 'Curriculum Unit', 'Multi-lesson thematic unit');
  await createModel('LessonStub', 'Lesson Stub', 'Lightweight lesson metadata');
  await createModel('DailyBread', 'Daily Bread', 'Daily devotional scripture content');
  await createModel('ResourceLink', 'Resource Link', 'Curated external link for tracks');

  // 3. Add fields to TrackPage
  console.log('\nAdding fields to TrackPage...');
  await createEnumerableField('TrackPage', 'track', 'Track', 'Track', { isRequired: true, isUnique: true });
  await createSimpleField('TrackPage', 'title', 'STRING', 'Title', { isRequired: true, isTitle: true });
  await createSimpleField('TrackPage', 'tagline', 'STRING', 'Tagline');
  await createSimpleField('TrackPage', 'description', 'RICHTEXT', 'Description');
  await createSimpleField('TrackPage', 'heroImageUrl', 'STRING', 'Hero Image URL');

  // 4. Add fields to CurriculumUnit
  console.log('\nAdding fields to CurriculumUnit...');
  await createEnumerableField('CurriculumUnit', 'track', 'Track', 'Track', { isRequired: true });
  await createSimpleField('CurriculumUnit', 'title', 'STRING', 'Title', { isRequired: true, isTitle: true });
  await createEnumerableField('CurriculumUnit', 'gradeBand', 'GradeBand', 'Grade Band', { isRequired: true });
  await createSimpleField('CurriculumUnit', 'oasStandards', 'STRING', 'OAS Standards', { isList: true });

  // 5. Add fields to LessonStub
  console.log('\nAdding fields to LessonStub...');
  await createEnumerableField('LessonStub', 'track', 'Track', 'Track', { isRequired: true });
  await createSimpleField('LessonStub', 'title', 'STRING', 'Title', { isRequired: true, isTitle: true });
  await createEnumerableField('LessonStub', 'gradeBand', 'GradeBand', 'Grade Band', { isRequired: true });
  await createSimpleField('LessonStub', 'estimatedMinutes', 'INT', 'Estimated Minutes');
  await createSimpleField('LessonStub', 'oasStandards', 'STRING', 'OAS Standards', { isList: true });
  await createSimpleField('LessonStub', 'isHomestead', 'BOOLEAN', 'Is Homestead', { isRequired: true });
  await createSimpleField('LessonStub', 'slug', 'STRING', 'Slug', { isRequired: true, isUnique: true });

  // 6. Add fields to DailyBread
  console.log('\nAdding fields to DailyBread...');
  await createSimpleField('DailyBread', 'date', 'DATE', 'Date', { isRequired: true, isUnique: true });
  await createSimpleField('DailyBread', 'scripture', 'STRING', 'Scripture', { isRequired: true });
  await createSimpleField('DailyBread', 'reference', 'STRING', 'Reference', { isRequired: true });
  await createSimpleField('DailyBread', 'reflection', 'RICHTEXT', 'Reflection');
  await createEnumerableField('DailyBread', 'track', 'Track', 'Track');

  // 7. Add fields to ResourceLink
  console.log('\nAdding fields to ResourceLink...');
  await createEnumerableField('ResourceLink', 'track', 'Track', 'Track', { isRequired: true });
  await createSimpleField('ResourceLink', 'title', 'STRING', 'Title', { isRequired: true, isTitle: true });
  await createSimpleField('ResourceLink', 'url', 'STRING', 'URL', { isRequired: true });
  await createSimpleField('ResourceLink', 'description', 'STRING', 'Description');
  await createEnumerableField('ResourceLink', 'sourceType', 'SourceType', 'Source Type', { isRequired: true });

  // 8. Create relations (after all models exist)
  console.log('\nCreating relations...');
  // TrackPage → CurriculumUnit (1:many)
  await createRelationalField('TrackPage', 'units', 'CurriculumUnit', 'Units', true);
  // CurriculumUnit → LessonStub (1:many)
  await createRelationalField('CurriculumUnit', 'lessonStubs', 'LessonStub', 'Lesson Stubs', true);
  // CurriculumUnit → TrackPage (many:1, reverse)
  await createRelationalField('CurriculumUnit', 'trackPage', 'TrackPage', 'Track Page', false);
  // LessonStub → CurriculumUnit (many:1)
  await createRelationalField('LessonStub', 'unit', 'CurriculumUnit', 'Unit', false);

  console.log('\n✅ Schema setup complete!');
  console.log('\nNext steps:');
  console.log('1. Go to Hygraph dashboard → Content');
  console.log('2. Create a TrackPage entry (e.g., CREATION_SCIENCE track)');
  console.log('3. Restart your Next.js dev server');
  console.log('4. Visit http://localhost:3000/curriculum/creation-science');
}

main().catch(err => {
  console.error('\n❌ Error:', err.message);
  process.exit(1);
});
