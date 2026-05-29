import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const env = readFileSync(join(here, '..', 'adeline-ui', '.env.local'), 'utf8');
const endpoint = env.match(/HYGRAPH_ENDPOINT=(.+)/)[1].trim();

const query = `{
  __schema { queryType { fields { name } } }
}`;

const res = await fetch(endpoint, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query }),
});
const data = await res.json();
const names = (data?.data?.__schema?.queryType?.fields || []).map((f) => f.name);
const targets = ['trackPage', 'trackPages', 'curriculumUnit', 'lessonStub', 'dailyBread', 'resourceLink'];
console.log('Found target queries:', targets.filter((t) => names.includes(t)));
console.log('All query fields:', names.join(', '));
