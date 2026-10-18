// Deterministic counterparts to interactive_models.py. The server recomputes saved results.
import type { ActivityInputs, ClassroomScene } from './classroom-client';
export function waterHeating(energyKj: number) {
  const q = energyKj * 10;
  if (q < 42) return { temperature: -20 + q / 2.1, solid: 1, liquid: 0, gas: 0 };
  if (q < 376) { const f = (q - 42) / 334; return { temperature: 0, solid: 1 - f, liquid: f, gas: 0 }; }
  if (q < 794.4) return { temperature: (q - 376) / 4.184, solid: 0, liquid: 1, gas: 0 };
  if (q < 3050.4) { const f = (q - 794.4) / 2256; return { temperature: 100, solid: 0, liquid: 1 - f, gas: f }; }
  return { temperature: 100 + (q - 3050.4) / 2, solid: 0, liquid: 0, gas: 1 };
}
export function massBalance(inputs: ActivityInputs) {
  const soda = Number(inputs.soda_g), vinegar = Number(inputs.vinegar_g), progress = Number(inputs.progress);
  const gas = Math.min(soda / 84.0066, vinegar * 0.05 / 60.052) * 44.0095 * progress;
  const initial = 150 + soda + vinegar, escaped = inputs.system === 'open' ? gas : 0;
  return { initial, scale: initial - escaped, escaped, retained: gas - escaped, gas };
}
export const moleculeTargets = { H2O: { H: 2, O: 1, C: 0 }, CO2: { H: 0, O: 2, C: 1 }, CH4: { H: 4, O: 0, C: 1 } } as const;
export function initialInputs(scene: ClassroomScene): ActivityInputs {
  if (scene.simulation) return { x: scene.simulation.x.initial, y: scene.simulation.y.initial };
  switch (scene.interaction?.kind) {
    case 'water_heating': return { energy_kj: 0 };
    case 'mass_balance': return { soda_g: 5, vinegar_g: 50, progress: 0, system: 'open' };
    case 'diagram': return { node_id: scene.interaction.nodes[0].id };
    default: return { H: 0, O: 0, C: 0 };
  }
}
