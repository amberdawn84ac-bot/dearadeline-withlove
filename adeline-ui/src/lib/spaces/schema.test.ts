import { describe, expect, it } from 'vitest';
import { spaceTurnRequestSchema } from './schema';

describe('Space schemas', () => {
  it('accepts one server-paced learner turn', () => {
    expect(spaceTurnRequestSchema.parse({
      studentId: 'student-1', planItemId: 'unit-1', userMessage: 'The jar doubled.', expectedVersion: 0,
    }).userMessage).toBe('The jar doubled.');
  });

  it('rejects a blank message', () => {
    expect(spaceTurnRequestSchema.safeParse({
      studentId: 'student-1', planItemId: 'unit-1', userMessage: '  ', expectedVersion: 0,
    }).success).toBe(false);
  });
});
