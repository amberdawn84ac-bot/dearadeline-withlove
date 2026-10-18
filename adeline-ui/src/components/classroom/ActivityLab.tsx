'use client';

import { useState } from 'react';
import type { ActivityInputs, ActivityWork, ClassroomScene, SavedActivity } from '@/lib/classroom-client';
import { initialInputs, massBalance, moleculeTargets, waterHeating } from '@/lib/classroom-models';

const button = 'min-h-11 rounded-xl border border-[#bba978] px-4 py-2 disabled:opacity-50';
const primary = 'min-h-11 rounded-xl bg-[#183d32] px-5 py-3 text-white disabled:opacity-50';
const number = (n: number) => n.toLocaleString(undefined, { maximumFractionDigits: 2 });

function Slider({ label, value, min, max, step = 1, unit = '', change }: { label: string; value: number; min: number; max: number; step?: number; unit?: string; change: (v: number) => void }) {
  return <label className="grid gap-2 rounded-xl bg-white p-3 font-medium">{label}: {number(value)} {unit}
    <input aria-label={label} type="range" min={min} max={max} step={step} value={value} onChange={e => change(Number(e.target.value))} className="h-11 w-full accent-emerald-800" />
  </label>;
}

function WaterView({ energy, change }: { energy: number; change: (n: number) => void }) {
  const model = waterHeating(energy);
  return <div className="space-y-4">
    <p>Follow 100 g of pure water from ice at −20°C. Pressure stays at one atmosphere.</p>
    <Slider label="Energy added" value={energy} min={0} max={330} step={0.1} unit="kJ" change={change} />
    <div className="grid grid-cols-2 gap-3" aria-live="polite"><output className="rounded-xl bg-white p-4 text-3xl">{number(model.temperature)}°C<span className="block text-sm">Temperature</span></output><p className="rounded-xl bg-white p-4 text-3xl">100 g<span className="block text-sm">Total water mass</span></p></div>
    <svg viewBox="0 0 360 220" role="img" aria-label={`Particle model: ${number(model.solid * 100)} percent ice, ${number(model.liquid * 100)} percent liquid, ${number(model.gas * 100)} percent vapor`} className="max-h-64 w-full rounded-xl bg-emerald-950">
      <style>{`@keyframes particleDrift{to{transform:translate(7px,-5px)}}@keyframes particleJiggle{to{transform:translate(1px,1px)}}@media(prefers-reduced-motion:reduce){.matter-particle{animation:none!important}}`}</style>
      <rect x="20" y="15" width="320" height="185" rx="12" fill="none" stroke="#c9a45c" strokeWidth="2" strokeDasharray="5 5" /><text x="32" y="38" fill="#fff9ec" fontSize="12">Particle sketch · not to scale</text>
      {Array.from({ length: 36 }, (_, i) => {
        const phase = i < Math.round(model.solid * 36) ? 'ice' : i < Math.round((model.solid + model.liquid) * 36) ? 'liquid' : 'vapor';
        const x = 45 + (i % 6) * 50, y = phase === 'vapor' ? 35 + Math.floor(i / 6) * 28 : 110 + Math.floor(i / 6) * 14;
        return <circle key={i} className="matter-particle" cx={x} cy={y} r="5" fill={phase === 'ice' ? '#e2f5ff' : phase === 'liquid' ? '#38bdf8' : '#e7c97a'} style={{ animation: `${phase === 'ice' ? 'particleJiggle' : 'particleDrift'} ${phase === 'vapor' ? 0.7 : 2}s ease-in-out ${-(i % 7) / 7}s infinite alternate` }} />;
      })}
    </svg>
    <p aria-live="polite">Ice {number(model.solid * 100)}% · Liquid {number(model.liquid * 100)}% · Vapor {number(model.gas * 100)}%</p>
    <p className="text-sm">The sketch follows the same sample, including vapor; it does not model a container or volume. Dots represent particles, not visible water vapor. This simplified model uses approximate heat capacities and latent heats, with no heat loss. Melting and boiling use energy while temperature stays level.</p>
    <details><summary className="cursor-pointer font-semibold">See the energy and temperature graph</summary><svg viewBox="0 0 400 230" role="img" aria-label="Heating curve with plateaus at zero and one hundred degrees Celsius" className="mt-3 w-full rounded-xl bg-white"><path d="M35 15V175H385" fill="none" stroke="#183d32" /><polyline points="35,170 39.2,150 72.6,150 114.44,50 340.04,50 365,25" fill="none" stroke="#a27e32" strokeWidth="3" /><circle cx={35 + energy} cy={150 - model.temperature} r="5" fill="#183d32" /><text x="2" y="155" fontSize="12">0°C</text><text x="0" y="55" fontSize="12">100°C</text>{[0, 100, 200, 300].map(tick => <g key={tick}><line x1={35 + tick} y1="175" x2={35 + tick} y2="180" stroke="#183d32" /><text x={35 + tick} y="195" textAnchor="middle" fontSize="12">{tick}</text></g>)}<text x="160" y="220" fontSize="14">Energy added (kJ)</text></svg></details>
  </div>;
}

function MassView({ inputs, change }: { inputs: ActivityInputs; change: (key: string, value: number | string) => void }) {
  const model = massBalance(inputs);
  return <div className="space-y-4">
    <p>Compare the scale reading with all matter accounted for. The container assembly is 150 g; vinegar contains 5% acetic acid by mass.</p>
    <div className="grid gap-3 sm:grid-cols-2"><Slider label="Baking soda" value={Number(inputs.soda_g)} min={0} max={50} unit="g" change={v => change('soda_g', v)} /><Slider label="Vinegar solution" value={Number(inputs.vinegar_g)} min={0} max={200} unit="g" change={v => change('vinegar_g', v)} /></div>
    <fieldset className="flex flex-wrap gap-3"><legend className="mb-2 font-semibold">System boundary</legend>{(['open', 'closed'] as const).map(value => <label key={value} className="flex min-h-11 items-center gap-2 rounded-xl border border-[#bba978] bg-white px-4 py-2"><input type="radio" name="mass-system" checked={inputs.system === value} onChange={() => change('system', value)} />{value === 'open' ? 'Open: gas can leave' : 'Closed: flexible gas collector'}</label>)}</fieldset>
    <Slider label="Reaction completed" value={Number(inputs.progress) * 100} min={0} max={100} step={5} unit="%" change={v => change('progress', v / 100)} />
    <div className="flex flex-wrap gap-3"><button className={button} onClick={() => change('progress', 1)}>Run to completion</button><button className={button} onClick={() => change('progress', 0)}>Start a fresh trial</button></div>
    <svg viewBox="0 0 360 180" role="img" aria-label={inputs.system === 'open' ? 'Gas leaving the container while remaining part of the total accounting' : 'Gas retained in a flexible collector above the container'} className="max-h-48 w-full rounded-xl bg-white"><path d="M95 55V140H235V55" fill="#dceff3" stroke="#183d32" strokeWidth="3" /><rect x="75" y="145" width="180" height="20" rx="5" fill="#183d32" />{inputs.system === 'closed' && <ellipse cx="165" cy="35" rx={25 + model.retained * 5} ry="22" fill="#c9a45c" opacity="0.6" />}{Array.from({ length: 8 }, (_, i) => <circle key={i} cx={inputs.system === 'open' ? 250 + i * 9 : 145 + i * 6} cy={inputs.system === 'open' ? 65 - (i % 4) * 14 : 32 + (i % 3) * 4} r={model.gas > 0 ? 3 : 0} fill="#9c741e" />)}</svg>
    <div className="grid gap-3 sm:grid-cols-2" aria-live="polite">{[['Initial mass', model.initial], ['Scale reading', model.scale], ['Escaped gas', model.escaped], ['Gas retained in collector', model.retained], ['Scale + escaped gas', model.scale + model.escaped]].map(([label, value]) => <p key={String(label)} className="rounded-xl bg-white p-3"><span className="block text-sm">{label}</span><b className="text-2xl">{number(Number(value))} g</b></p>)}</div>
    <p className="text-sm">The model uses reaction proportions and the limiting reactant. It omits dissolved CO₂, evaporation and measurement error. The closed assembly includes its flexible collector in the initial mass. Changing an input defines a new trial.</p>
  </div>;
}

function DiagramView({ scene, inputs, change, narratedNode }: { scene: ClassroomScene; inputs: ActivityInputs; change: (key: string, value: string) => void; narratedNode?: string | null }) {
  const spec = scene.interaction!;
  const selected = spec.nodes.find(node => node.id === (narratedNode ?? inputs.node_id)) ?? spec.nodes[0];
  return <div className="space-y-4">
    <p>Select a part, read its explanation, and follow a connection. Record the parts that help you explain the whole.</p>
    <svg viewBox={`0 0 600 ${Math.ceil(spec.nodes.length / 2) * 110 + 20}`} role="img" aria-label="Diagram showing the connections between parts; select a named button below to inspect one" className="hidden w-full rounded-xl bg-white sm:block">
      <defs><marker id="connection-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0L8 4L0 8Z" fill="#a27e32" /></marker></defs>
      {spec.edges.map((edge, i) => { const from = spec.nodes.findIndex(n => n.id === edge.source), to = spec.nodes.findIndex(n => n.id === edge.target); const x = 150 + from % 2 * 300, y = 50 + Math.floor(from / 2) * 110, dx = (to % 2 - from % 2) * 300, dy = (Math.floor(to / 2) - Math.floor(from / 2)) * 110, inset = Math.min(dx ? 120 / Math.abs(dx) : Infinity, dy ? 25 / Math.abs(dy) : Infinity); return <line key={i} x1={x + dx * inset} y1={y + dy * inset} x2={x + dx * (1 - inset)} y2={y + dy * (1 - inset)} stroke="#a27e32" strokeWidth="2" markerEnd="url(#connection-arrow)" />; })}
      {spec.nodes.map((node, i) => <g key={node.id}><rect x={30 + i % 2 * 300} y={25 + Math.floor(i / 2) * 110} width="240" height="50" rx="12" fill={selected.id === node.id ? '#183d32' : '#f2ead7'} /><text x={150 + i % 2 * 300} y={55 + Math.floor(i / 2) * 110} textAnchor="middle" fontSize="16" fill={selected.id === node.id ? '#fff9ec' : '#183d32'}>{node.label.length > 26 ? node.label.slice(0, 25) + '…' : node.label}</text></g>)}
    </svg>
    <div className="grid gap-3 sm:grid-cols-2" aria-label="Diagram parts">{spec.nodes.map(node => <button key={node.id} aria-pressed={node.id === selected.id} onClick={() => change('node_id', node.id)} className={`${button} bg-white text-left ${node.id === selected.id ? 'ring-2 ring-emerald-700' : ''}`}>{node.label}</button>)}</div>
    <article aria-live="polite" className="rounded-xl bg-white p-5"><h3 className="text-xl font-semibold">{selected.label}</h3><p className="mt-3 leading-7">{selected.detail}</p></article>
    <ul aria-label="Connections" className="space-y-3">{spec.edges.filter(edge => edge.source === selected.id || edge.target === selected.id).map((edge, i) => <li key={i} className="rounded-xl border border-[#c9bfa9] bg-white p-3"><b>{spec.nodes.find(n => n.id === edge.source)?.label}</b> → {edge.label} → <b>{spec.nodes.find(n => n.id === edge.target)?.label}</b></li>)}</ul>
  </div>;
}

function MoleculeView({ scene, inputs, change }: { scene: ClassroomScene; inputs: ActivityInputs; change: (key: string, value: number) => void }) {
  const formula = scene.interaction!.formula, target = moleculeTargets[formula];
  const matches = (['H', 'O', 'C'] as const).every(atom => Number(inputs[atom]) === target[atom]);
  return <div className="space-y-4">
    <p className="text-xl font-semibold">Build the composition of {formula}</p>
    <div className="grid grid-cols-3 gap-3">{(['H', 'O', 'C'] as const).map(atom => <label key={atom} className="grid gap-2 rounded-xl bg-white p-3">{atom === 'H' ? 'Hydrogen' : atom === 'O' ? 'Oxygen' : 'Carbon'}<input aria-label={`${atom} atoms`} type="number" min={0} max={10} step={1} value={inputs[atom]} onChange={e => change(atom, Math.min(10, Math.max(0, Math.round(Number(e.target.value) || 0))))} className="min-h-11 w-full rounded-lg border p-2" /></label>)}</div>
    <div aria-label="All selected atoms" className="flex min-h-24 flex-wrap gap-2 rounded-xl bg-white p-4">{(['H', 'O', 'C'] as const).flatMap(atom => Array.from({ length: Number(inputs[atom]) }, (_, i) => <span key={`${atom}-${i}`} className={`flex h-11 w-11 items-center justify-center rounded-full border-2 border-emerald-950 font-bold ${atom === 'H' ? 'bg-white' : atom === 'O' ? 'bg-sky-200' : 'bg-amber-200'}`}>{atom}</span>))}</div>
    <p aria-live="polite" className="rounded-xl bg-white p-4">{matches ? 'These counts match the target composition. Explain how you know.' : 'Compare each atom count with the formula. Extra atoms remain extra; none disappear.'}</p>
    <div className="overflow-x-auto"><table className="w-full rounded-xl bg-white text-left text-sm"><caption className="p-2 text-left font-semibold">Account for every atom</caption><thead><tr><th className="p-2">Atom</th><th className="p-2">Selected</th><th className="p-2">Formula needs</th><th className="p-2">Extra</th></tr></thead><tbody>{(['H', 'O', 'C'] as const).map(atom => <tr key={atom}><th className="p-2">{atom}</th><td className="p-2">{inputs[atom]}</td><td className="p-2">{target[atom]}</td><td className="p-2">{Math.max(0, Number(inputs[atom]) - target[atom])}</td></tr>)}</tbody></table></div>
    <p className="text-sm">This is a composition model. Choosing atoms on a screen is not a method for producing these substances in real life.</p>
  </div>;
}

function NumericView({ scene, inputs, change }: { scene: ClassroomScene; inputs: ActivityInputs; change: (key: string, value: number) => void }) {
  const spec = scene.simulation!, x = Number(inputs.x), y = Number(inputs.y);
  const value = spec.model === 'mixture_fraction' ? x / (x + y) : x * y;
  return <div className="space-y-4">{(['x', 'y'] as const).map(axis => <Slider key={axis} label={spec[axis].label} value={Number(inputs[axis])} min={spec[axis].minimum} max={spec[axis].maximum} step={spec[axis].step} unit={spec[axis].unit} change={v => change(axis, v)} />)}<output aria-live="polite" className="block rounded-xl bg-white p-4 text-3xl">{number(value)} {spec.output_unit}<span className="block text-base">{spec.output_label}</span></output>{spec.model === 'rectangle_area' && <svg viewBox="0 0 300 160" role="img" aria-label={`Rectangle with sides ${x} and ${y}`} className="w-full"><rect x="20" y="10" width={x / spec.x.maximum * 260} height={y / spec.y.maximum * 140} fill="#c9a45c" /></svg>}<p>{spec.explanation}</p></div>;
}

function describeTrial(scene: ClassroomScene, trial: ActivityInputs) {
  if (scene.interaction?.kind === 'water_heating') { const m = waterHeating(Number(trial.energy_kj)); return `${number(Number(trial.energy_kj))} kJ → ${number(m.temperature)}°C; ice ${number(m.solid * 100)}%, liquid ${number(m.liquid * 100)}%, vapor ${number(m.gas * 100)}%`; }
  if (scene.interaction?.kind === 'mass_balance') { const m = massBalance(trial); return `${trial.system === 'open' ? 'Open' : 'Closed'}; soda ${trial.soda_g} g, vinegar ${trial.vinegar_g} g, reaction ${number(Number(trial.progress) * 100)}% → scale ${number(m.scale)} g, escaped gas ${number(m.escaped)} g`; }
  if (scene.interaction?.kind === 'diagram') return `Inspected: ${scene.interaction.nodes.find(n => n.id === trial.node_id)?.label ?? ''}`;
  if (scene.interaction?.kind === 'molecule_builder') return `Hydrogen ${trial.H}; oxygen ${trial.O}; carbon ${trial.C}`;
  const spec = scene.simulation!, x = Number(trial.x), y = Number(trial.y);
  return `${spec.x.label}: ${x} ${spec.x.unit}; ${spec.y.label}: ${y} ${spec.y.unit} → ${spec.output_label}: ${number(spec.model === 'mixture_fraction' ? x / (x + y) : x * y)} ${spec.output_unit}`;
}

export default function ActivityLab({ scene, saved, saving, onSave, onDirty, narratedNode }: { scene: ClassroomScene; saved?: { text: string; activity?: SavedActivity }; saving: boolean; onSave: (text: string, activity: ActivityWork) => Promise<void>; onDirty: (dirty: boolean) => void; narratedNode?: string | null }) {
  const [earlierNotes] = useState(saved?.activity?.earlier_notes ?? (saved && !saved.activity ? saved.text : ''));
  const [prediction, setPrediction] = useState(saved?.activity?.prediction ?? '');
  const [revealed, setRevealed] = useState(!!saved?.activity);
  const [inputs, setInputs] = useState<ActivityInputs>(saved?.activity?.stage === 'observation' ? saved.activity.inputs : initialInputs(scene));
  const [trials, setTrials] = useState<ActivityInputs[]>(saved?.activity?.trials ?? []);
  const [observation, setObservation] = useState(saved?.activity?.stage === 'observation' ? saved.text : '');
  const [error, setError] = useState('');
  const spec = scene.interaction ?? scene.simulation!;
  function change(key: string, value: number | string) { setInputs(current => ({ ...current, [key]: value })); onDirty(true); }
  async function submit(stage: ActivityWork['stage']) {
    setError('');
    try {
      await onSave(stage === 'prediction' ? prediction : observation, { stage, prediction, inputs: stage === 'prediction' ? {} : inputs, trials: stage === 'prediction' ? [] : trials });
      setRevealed(true); onDirty(false);
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Your work could not be saved.'); }
  }
  return <section aria-label="Investigation activity" className="my-6 space-y-5 rounded-2xl border border-[#d9cfbc] bg-[#f2ead7] p-4 sm:p-6">
    <h3 className="text-2xl font-semibold">{revealed ? 'Explore and explain' : 'Before you try it'}</h3>
    {earlierNotes && <details><summary className="cursor-pointer font-semibold">Earlier saved notes</summary><p className="mt-3 whitespace-pre-line rounded-xl bg-white p-3">{earlierNotes}</p></details>}
    <p>{spec.prediction_prompt}</p>
    {!revealed ? <div className="space-y-3"><label className="grid gap-2 font-semibold">Your prediction<textarea aria-label="Your prediction" maxLength={1500} value={prediction} disabled={saving} onChange={e => { setPrediction(e.target.value); onDirty(!!e.target.value.trim()); }} className="min-h-24 w-full rounded-xl border border-[#c9bfa9] bg-white p-3" /></label><button className={primary} disabled={saving || !prediction.trim()} onClick={() => void submit('prediction')}>{saving ? 'Saving prediction…' : 'Save prediction and explore'}</button></div> : <>
      <details><summary className="cursor-pointer font-semibold">Your original prediction</summary><p className="mt-3 whitespace-pre-line rounded-xl bg-white p-3">{prediction}</p></details>
      <fieldset disabled={saving} className="min-w-0 space-y-4">
        {scene.simulation && <NumericView scene={scene} inputs={inputs} change={change} />}
        {scene.interaction?.kind === 'water_heating' && <WaterView energy={Number(inputs.energy_kj)} change={v => change('energy_kj', v)} />}
        {scene.interaction?.kind === 'mass_balance' && <MassView inputs={inputs} change={change} />}
        {scene.interaction?.kind === 'diagram' && <DiagramView scene={scene} inputs={inputs} change={change} narratedNode={narratedNode} />}
        {scene.interaction?.kind === 'molecule_builder' && <MoleculeView scene={scene} inputs={inputs} change={change} />}
        <button className={button} disabled={trials.length >= 12} onClick={() => { setTrials(current => [...current, { ...inputs }]); onDirty(true); }}>Record this result</button>
        {trials.length > 0 && <ol aria-label="Recorded trials" className="list-decimal space-y-2 pl-5">{trials.map((trial, i) => <li key={i} className="break-words text-sm">{describeTrial(scene, trial)}</li>)}</ol>}
        {trials.length > 0 && <button className={button} onClick={() => { setTrials([]); onDirty(true); }}>Start a new comparison</button>}
        <p>{spec.observation_prompt}</p>
        <label className="grid gap-2 font-semibold">Your observations<textarea aria-label="Your observations" maxLength={8000} value={observation} onChange={e => { setObservation(e.target.value); onDirty(true); }} className="min-h-28 w-full rounded-xl border border-[#c9bfa9] bg-white p-3" /></label>
        <button className={primary} disabled={saving || !observation.trim() || !trials.length} onClick={() => void submit('observation')}>{saving ? 'Saving…' : 'Save observations and results'}</button>
      </fieldset>
    </>}
    {error && <p role="alert" className="text-red-800">{error}</p>}
  </section>;
}
