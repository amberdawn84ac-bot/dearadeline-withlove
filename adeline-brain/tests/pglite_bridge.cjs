const {PGlite} = require('@electric-sql/pglite');
const readline = require('node:readline');
const db = new PGlite();
const lines = readline.createInterface({input:process.stdin});
let chain = Promise.resolve();
lines.on('line', line => { chain = chain.then(async () => {
  try { const q=JSON.parse(line); const result=q.exec ? await db.exec(q.sql) : await db.query(q.sql,q.args); process.stdout.write(JSON.stringify({rows:result.rows ?? []})+'\n'); }
  catch(e) { process.stdout.write(JSON.stringify({error:e.message})+'\n'); }
}); });
