import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ScienceLabNotebook } from './ScienceLabNotebook';

const block = { title: 'Growth lab', block_type: 'SCIENCE_LAB', metadata: {
  resource_id: 'issued-1', teaching: 'Test a claim using actual measurements.', materials: ['plants'], steps: ['Measure the plants.'],
  lab: { question: 'Does exposure matter?', investigation_kind: 'controlled_experiment', prediction_prompt: 'Your prediction', independent_variable: 'light hours', dependent_variable: 'height', controls_or_limits: ['Same soil'], safety: ['Wash hands'],
    columns: [{ key: 'hours', label: 'Light', unit: 'h', kind: 'number' }, { key: 'height', label: 'Height', unit: 'cm', kind: 'number' }], graph: { x_key: 'hours', y_key: 'height', kind: 'scatter' },
    claim_prompt: 'Your claim', evidence_prompt: 'Your evidence', reasoning_prompt: 'Your reasoning' },
} };

describe('structured science lab notebook', () => {
  it('plots learner measurements and submits an unfinished notebook without invented data', () => {
    const submit = vi.fn(); render(<ScienceLabNotebook block={block} onSubmit={submit} />);
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Light, row 1'), { target: { value: '4' } });
    fireEvent.change(screen.getByLabelText('Height, row 1'), { target: { value: '5.2' } });
    fireEvent.change(screen.getByLabelText('Light, row 2'), { target: { value: '8' } });
    fireEvent.change(screen.getByLabelText('Height, row 2'), { target: { value: '7' } });
    expect(screen.getByRole('img', { name: /Your measurements/ })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Save notebook with Adeline' }));
    const payload = JSON.parse(submit.mock.calls[0][0].split('\n')[1]);
    expect(payload.resource_id).toBe('issued-1');
    expect(payload.rows[0]).toEqual({ hours: '4', height: '5.2' });
    expect(payload.claim).toBe('');
    expect(payload.rows[2]).toEqual({ hours: '', height: '' });
  });
  it('reopens saved measurements and a saved conclusion', () => {
    const saved = { ...block, metadata: { ...block.metadata, notebook: { resource_id: 'issued-1', rows: [{ hours: '4', height: '5.2' }], prediction: 'More light may help', claim: 'Growth differed', evidence: '5.2 cm', reasoning: 'Other factors may matter' } } };
    render(<ScienceLabNotebook block={saved} />);
    expect(screen.getByLabelText('Height, row 1')).toHaveValue(5.2);
    expect(screen.getByDisplayValue('Growth differed')).toBeInTheDocument();
  });
});
