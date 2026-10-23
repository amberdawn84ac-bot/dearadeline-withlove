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
export function airVolume(volumeMl: number) {
  const pressure = 101.325 * (50 / volumeMl);
  return { pressure, product: pressure * volumeMl };
}
export const matterMenu = [
  ['color', 'Color you can see'], ['shape', 'A shape of its own'], ['texture', 'Texture you can feel'],
  ['space', 'Takes up space'], ['mass', 'Has mass you can feel or measure'], ['cold', 'Feels cold'],
  ['pours', 'Pours or flows'], ['invisible', 'The material itself is invisible'],
  ['compressible', 'You can squeeze it smaller and it pushes back'], ['fixed_shape', 'Keeps its own shape'],
] as const;
export const matterSamples = {
  ice_cube: { title: 'Ice cube you can hold', detail: 'A solid piece of frozen pure water, about the size of a walnut, on a plate. It has not melted.' },
  liquid_water: { title: 'Glass of liquid water', detail: 'A clear glass of liquid water at room temperature.' },
  sealed_air: { title: 'Air in a sealed syringe', detail: 'A syringe blocked at the tip, partly filled with air, with the plunger free to move. No water is inside.' },
  dry_sand: { title: 'Spoon of dry sand', detail: 'Dry sand on a plate. The grains are visible and can be poured.' },
} as const;
export function initialInputs(scene: ClassroomScene): ActivityInputs {
  if (scene.simulation) return { x: scene.simulation.x.initial, y: scene.simulation.y.initial };
  switch (scene.interaction?.kind) {
    case 'water_heating': return { energy_kj: 0 };
    case 'mass_balance': return { soda_g: 5, vinegar_g: 50, progress: 0, system: 'open' };
    case 'diagram': return { node_id: scene.interaction.nodes[0].id };
    case 'air_volume': return { volume_ml: 50 };
    case 'graph_compare': return { index: 0, choice: 'a' };
    case 'sequence': return { order: (scene.interaction.steps ?? []).map(step => step.id).join(',') };
    case 'matching': return { matches: (scene.interaction.pairs ?? []).map(pair => `${pair.id}:`).join(',') };
    case 'matter_properties': return { selected: '' };
    default: return { H: 0, O: 0, C: 0 };
  }
}
