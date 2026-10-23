import { describe, expect, it } from 'vitest';
import { airVolume, massBalance, waterHeating } from '../classroom-models';

describe('Classroom model invariants', () => {
  it('has ice warming, melting, liquid warming, boiling and vapor warming', () => {
    expect(waterHeating(0)).toEqual({ temperature: -20, solid: 1, liquid: 0, gas: 0 });
    expect(waterHeating(20.9).temperature).toBe(0);
    expect(waterHeating(20.9).solid).toBeCloseTo(.5);
    expect(waterHeating(192.24).temperature).toBe(100);
    expect(waterHeating(192.24).gas).toBeCloseTo(.5);
    expect(waterHeating(330).temperature).toBeGreaterThan(100);
  });
  it('preserves particle fractions throughout every supported energy step', () => {
    let previous = -20;
    for (let tenth = 0; tenth <= 3300; tenth++) {
      const m = waterHeating(tenth / 10);
      expect(m.solid + m.liquid + m.gas).toBeCloseTo(1);
      expect(m.temperature).toBeGreaterThanOrEqual(previous - 1e-10);
      previous = m.temperature;
    }
  });
  it('accounts for escaped gas and never reports a mass below the assembly', () => {
    for (const soda_g of [0, .1, 5, 50]) for (const vinegar_g of [0, 10, 50, 200]) for (const progress of [0, .5, 1]) for (const system of ['open', 'closed']) {
      const m = massBalance({ soda_g, vinegar_g, progress, system });
      expect(m.scale + m.escaped).toBeCloseTo(m.initial);
      expect(m.scale).toBeGreaterThanOrEqual(150);
      if (system === 'closed') expect(m.scale).toBe(m.initial);
    }
  });
  it('uses the limiting reactant to calculate carbon dioxide', () => {
    expect(massBalance({ soda_g: .840066, vinegar_g: 120.104, progress: 1, system: 'open' }).gas).toBeCloseTo(.440095);
    expect(massBalance({ soda_g: 50, vinegar_g: 10, progress: 1, system: 'open' }).gas).toBeCloseTo(.5 / 60.052 * 44.0095);
  });
  it('keeps sealed-air pressure times volume constant', () => {
    for (const volume of [20, 50, 75, 100]) expect(airVolume(volume).product).toBeCloseTo(5066.25);
    expect(airVolume(50).pressure).toBeCloseTo(101.325);
    expect(airVolume(25).pressure).toBeCloseTo(202.65);
  });
});
