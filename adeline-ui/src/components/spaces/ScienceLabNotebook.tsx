'use client';
import { useState } from 'react';

interface Column { key: string; label: string; unit: string; kind: 'number' | 'text' }
interface Notebook { resource_id: string; prediction: string; rows: Record<string, string>[]; claim: string; evidence: string; reasoning: string }
interface Lab {
  question: string; investigation_kind: string; prediction_prompt: string;
  independent_variable: string; dependent_variable: string; controls_or_limits: string[]; safety: string[];
  columns: Column[]; graph?: { x_key: string; y_key: string; kind: 'scatter' | 'line' } | null;
  claim_prompt: string; evidence_prompt: string; reasoning_prompt: string;
}

function MeasurementGraph({ lab, rows }: { lab: Lab; rows: Record<string, string>[] }) {
  const graph = lab.graph;
  if (!graph) return null;
  const points = rows.filter(row => row[graph.x_key]?.trim() && row[graph.y_key]?.trim())
    .map(row => ({ x: Number(row[graph.x_key]), y: Number(row[graph.y_key]) }))
    .filter(p => Number.isFinite(p.x) && Number.isFinite(p.y)).sort((a, b) => a.x - b.x);
  if (points.length < 2) return <p className="text-sm">Enter at least two numerical measurements to see the graph.</p>;
  const xmin = Math.min(...points.map(p => p.x)), xmax = Math.max(...points.map(p => p.x));
  const ymin = Math.min(...points.map(p => p.y)), ymax = Math.max(...points.map(p => p.y));
  const position = (p: { x: number; y: number }) => ({ x: 55 + ((p.x - xmin) / (xmax - xmin || 1)) * 290, y: 170 - ((p.y - ymin) / (ymax - ymin || 1)) * 130 });
  const xcol = lab.columns.find(c => c.key === graph.x_key), ycol = lab.columns.find(c => c.key === graph.y_key);
  const label = (c?: Column) => c ? `${c.label}${c.unit ? ` (${c.unit})` : ''}` : '';
  return <figure><svg viewBox="0 0 400 240" role="img" aria-label={`Your measurements: ${label(ycol)} against ${label(xcol)}`} className="w-full max-w-xl rounded-lg bg-white">
    <path d="M55 35 V170 H350" fill="none" stroke="#2F4731" />
    {[0, 0.5, 1].map(t => <g key={t}><text x={50} y={174 - t * 130} textAnchor="end" fontSize="10">{(ymin + t * (ymax - ymin)).toPrecision(3)}</text><text x={55 + t * 290} y={188} textAnchor="middle" fontSize="10">{(xmin + t * (xmax - xmin)).toPrecision(3)}</text></g>)}
    {graph.kind === 'line' && <polyline points={points.map(p => { const pos = position(p); return `${pos.x},${pos.y}`; }).join(' ')} fill="none" stroke="#BD6809" strokeWidth="2" />}
    {points.map((p, i) => { const pos = position(p); return <circle key={i} cx={pos.x} cy={pos.y} r="4" fill="#2F4731"><title>{`${p.x}, ${p.y}`}</title></circle>; })}
    <text x="200" y="218" textAnchor="middle" fontSize="11">{label(xcol)}</text><text transform="translate(12 100) rotate(-90)" textAnchor="middle" fontSize="11">{label(ycol)}</text>
  </svg><figcaption className="text-xs">Only your entered measurements are plotted. A pattern alone does not prove its cause.</figcaption></figure>;
}

export function ScienceLabNotebook({ block, onSubmit }: { block: Record<string, unknown>; onSubmit?: (text: string) => void }) {
  const metadata = block.metadata as { lab: Lab; resource_id: string; teaching: string; materials: string[]; steps: string[]; notebook?: Notebook };
  const lab = metadata.lab;
  const emptyRow = () => Object.fromEntries(lab.columns.map(c => [c.key, '']));
  const [notebook, setNotebook] = useState<Notebook>(metadata.notebook ?? { resource_id: metadata.resource_id, prediction: '', rows: [emptyRow(), emptyRow(), emptyRow()], claim: '', evidence: '', reasoning: '' });
  const [notice, setNotice] = useState('');
  function submit() {
    const text = `Lab notebook submission:\n${JSON.stringify(notebook)}`;
    if (text.length > 4000) { setNotice('Shorten your notes before sending this notebook.'); return; }
    onSubmit?.(text); setNotice('Sent to Adeline. Her reply will confirm whether the notebook was saved.');
  }
  const inputClass = 'w-full rounded-lg border border-[#CFC1A8] bg-white p-2 text-sm';
  return <section className="my-3 space-y-4 rounded-2xl border border-[#CFC1A8] bg-[#FFFDF7] p-4">
    <h3 className="font-bold text-[#2F4731]">{String(block.title || 'Science lab')}</h3>
    <p className="text-sm whitespace-pre-wrap">{metadata.teaching}</p><p className="font-bold">{lab.question}</p>
    {lab.investigation_kind === 'simulation' && <p className="text-sm font-bold">Simulation — these results describe a model, not measurements of a real specimen.</p>}
    <p className="text-sm">Materials: {metadata.materials.join(', ') || 'Check with Adeline before starting.'}</p>
    <aside className="rounded-xl bg-[#F4E6CE] p-3 text-sm"><p className="font-bold">Before starting</p><ul className="list-disc pl-5">{lab.safety.map((s, i) => <li key={i}>{s}</li>)}</ul></aside>
    {(lab.independent_variable || lab.dependent_variable) && <p className="text-sm">Change: {lab.independent_variable || 'No manipulated variable'}. Measure: {lab.dependent_variable || 'Record observations'}.</p>}
    <div className="text-sm"><p className="font-bold">Controls and limits</p><ul className="list-disc pl-5">{lab.controls_or_limits.map((s, i) => <li key={i}>{s}</li>)}</ul></div>
    <label className="grid gap-1 text-sm">{lab.prediction_prompt}<textarea className={inputClass} maxLength={300} value={notebook.prediction} onChange={e => setNotebook(n => ({ ...n, prediction: e.target.value }))} /></label>
    <ol className="list-decimal space-y-2 pl-5 text-sm">{metadata.steps.map((s, i) => <li key={i}>{s}</li>)}</ol>
    <div className="overflow-x-auto"><table className="w-full text-sm"><caption className="pb-2 text-left font-bold">Your observations and measurements</caption><thead><tr>{lab.columns.map(c => <th key={c.key} scope="col" className="p-2 text-left">{c.label}{c.unit ? ` (${c.unit})` : ''}</th>)}</tr></thead><tbody>{notebook.rows.map((row, i) => <tr key={i}>{lab.columns.map(c => <td key={c.key} className="p-1"><input aria-label={`${c.label}, row ${i + 1}`} type={c.kind === 'number' ? 'number' : 'text'} step="any" maxLength={40} className={inputClass} value={row[c.key] || ''} onChange={e => setNotebook(n => ({ ...n, rows: n.rows.map((r, index) => index === i ? { ...r, [c.key]: e.target.value.slice(0, 40) } : r) }))} /></td>)}</tr>)}</tbody></table></div>
    <button type="button" disabled={notebook.rows.length >= 12} onClick={() => setNotebook(n => ({ ...n, rows: [...n.rows, emptyRow()] }))} className="text-sm font-bold underline">Add measurement row</button>
    <MeasurementGraph lab={lab} rows={notebook.rows} />
    {(['claim', 'evidence', 'reasoning'] as const).map(key => <label key={key} className="grid gap-1 text-sm"><span className="font-bold capitalize">{key}</span>{lab[`${key}_prompt`]}<textarea className={inputClass} rows={2} maxLength={300} value={notebook[key]} onChange={e => setNotebook(n => ({ ...n, [key]: e.target.value }))} /></label>)}
    {onSubmit && <button type="button" onClick={submit} className="rounded-xl bg-[#2F4731] px-4 py-2 text-sm font-bold text-white">Save notebook with Adeline</button>}
    {notice && <p role="status" className="text-sm">{notice}</p>}
    <p className="text-xs">You can save unfinished work. Your explanation and evidence are reviewed separately from filling in the notebook.</p>
  </section>;
}
