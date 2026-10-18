import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import ActivityLab from '../ActivityLab';
import type { ClassroomScene } from '@/lib/classroom-client';

const scene: ClassroomScene = {
  id: 'heat', title: 'Where does the energy go?', type: 'interactive', content: 'Explore the water model.',
  key_points: [], actions: [{ role_id: 'adeline', text: 'Predict what will change.' }],
  learner_task: 'Explain what happened.', success_criteria: ['Use recorded results.'],
  family_roles: { elementary: 'Describe ice and water.', middle: 'Explain energy changes.', high_school: 'Evaluate model assumptions.' },
  question: null, simulation: null, materials: [], steps: [],
  interaction: { kind: 'water_heating', prediction_prompt: 'What happens as energy enters the ice?', observation_prompt: 'Compare your prediction with the results.', nodes: [], edges: [], formula: 'H2O' },
};
const prediction = 'Temperature rises until the ice melts.';

describe('Investigation activities', () => {
  it('keeps results hidden until the prediction is successfully saved', async () => {
    const save = vi.fn().mockRejectedValueOnce(new Error('Connection lost')).mockResolvedValue(undefined);
    const dirty = vi.fn();
    render(<ActivityLab scene={scene} saving={false} onSave={save} onDirty={dirty} />);
    expect(screen.queryByLabelText('Energy added')).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Your prediction'), { target: { value: prediction } });
    fireEvent.click(screen.getByText('Save prediction and explore'));
    await screen.findByText('Connection lost');
    expect(screen.queryByLabelText('Energy added')).not.toBeInTheDocument();
    fireEvent.click(screen.getByText('Save prediction and explore'));
    await screen.findByLabelText('Energy added');
    expect(save).toHaveBeenLastCalledWith(prediction, { stage: 'prediction', prediction, inputs: {}, trials: [] });
    expect(dirty).toHaveBeenLastCalledWith(false);
  });
  it('records observations and selected trials together, keeping the original prediction', async () => {
    const save = vi.fn().mockResolvedValue(undefined), dirty = vi.fn();
    render(<ActivityLab scene={scene} saved={{ text: prediction, activity: { stage: 'prediction', prediction, inputs: {}, trials: [] } }} saving={false} onSave={save} onDirty={dirty} />);
    fireEvent.change(screen.getByLabelText('Energy added'), { target: { value: '20.9' } });
    expect(screen.getByText('Temperature').parentElement).toHaveTextContent('0°C');
    fireEvent.click(screen.getByText('Record this result'));
    expect(screen.getByRole('list', { name: 'Recorded trials' })).toHaveTextContent('20.9 kJ → 0°C');
    fireEvent.change(screen.getByLabelText('Your observations'), { target: { value: 'Melting used energy without warming the water.' } });
    fireEvent.click(screen.getByText('Save observations and results'));
    await waitFor(() => expect(save).toHaveBeenCalledWith('Melting used energy without warming the water.', { stage: 'observation', prediction, inputs: { energy_kj: 20.9 }, trials: [{ energy_kj: 20.9 }] }));
    expect(screen.queryByLabelText('Your prediction')).not.toBeInTheDocument();
  });
  it('restores saved controls, predictions, trials and observations', () => {
    render(<ActivityLab scene={scene} saved={{ text: 'Half the ice melted.', activity: { stage: 'observation', prediction, inputs: { energy_kj: 20.9 }, trials: [{ energy_kj: 20.9 }] } }} saving={false} onSave={vi.fn()} onDirty={vi.fn()} />);
    expect(screen.getByLabelText('Energy added')).toHaveValue('20.9');
    expect(screen.getByLabelText('Your observations')).toHaveValue('Half the ice melted.');
    expect(screen.getByText(prediction)).toBeInTheDocument();
    expect(screen.getByRole('list', { name: 'Recorded trials' })).toHaveTextContent('50%');
  });
  it('accounts for gas that escapes instead of destroying matter', () => {
    const massScene: ClassroomScene = { ...scene, interaction: { ...scene.interaction!, kind: 'mass_balance' } };
    render(<ActivityLab scene={massScene} saved={{ text: prediction, activity: { stage: 'prediction', prediction, inputs: {}, trials: [] } }} saving={false} onSave={vi.fn()} onDirty={vi.fn()} />);
    fireEvent.click(screen.getByText('Run to completion'));
    expect(screen.getByText('Scale + escaped gas').parentElement).toHaveTextContent('205 g');
    expect(screen.getByText('Scale reading').parentElement).not.toHaveTextContent('50.85');
    fireEvent.click(screen.getByLabelText('Closed: flexible gas collector'));
    expect(screen.getByText('Scale reading').parentElement).toHaveTextContent('205 g');
  });
  it('supports keyboard-accessible diagram inspection and actual relationships', () => {
    const diagram: ClassroomScene = { ...scene, interaction: { ...scene.interaction!, kind: 'diagram', nodes: [{ id: 'a', label: 'Evidence', detail: 'An observation we can inspect.' }, { id: 'b', label: 'Claim', detail: 'An explanation that can be tested.' }], edges: [{ source: 'a', target: 'b', label: 'supports or challenges' }] } };
    render(<ActivityLab scene={diagram} saved={{ text: prediction, activity: { stage: 'prediction', prediction, inputs: {}, trials: [] } }} saving={false} onSave={vi.fn()} onDirty={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: 'Claim' }));
    expect(screen.getByText('An explanation that can be tested.')).toBeInTheDocument();
    expect(screen.getByRole('list', { name: 'Connections' })).toHaveTextContent('supports or challenges');
    fireEvent.click(screen.getByText('Record this result'));
    expect(screen.getByRole('list', { name: 'Recorded trials' })).toHaveTextContent('Inspected: Claim');
  });
  it('rejects extra carbon as a correct water composition', () => {
    const molecule: ClassroomScene = { ...scene, interaction: { ...scene.interaction!, kind: 'molecule_builder' } };
    render(<ActivityLab scene={molecule} saved={{ text: prediction, activity: { stage: 'prediction', prediction, inputs: {}, trials: [] } }} saving={false} onSave={vi.fn()} onDirty={vi.fn()} />);
    fireEvent.change(screen.getByLabelText('H atoms'), { target: { value: '2' } });
    fireEvent.change(screen.getByLabelText('O atoms'), { target: { value: '1' } });
    expect(screen.getByText(/These counts match/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('C atoms'), { target: { value: '1' } });
    expect(screen.queryByText(/These counts match/)).not.toBeInTheDocument();
    expect(screen.getByText(/Extra atoms remain extra/)).toBeInTheDocument();
  });
});
