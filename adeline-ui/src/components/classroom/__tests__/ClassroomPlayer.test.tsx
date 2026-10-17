import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import ClassroomPlayer from '../ClassroomPlayer';
import type { ClassroomScene, ClassroomState } from '@/lib/classroom-client';
const mocks = vi.hoisted(() => ({ submit: vi.fn(), talk: vi.fn() }));
vi.mock('@/lib/classroom-client', () => ({ submitClassroomResponse: mocks.submit, talkToClassroom: mocks.talk }));
const scene: ClassroomScene = {
  id: 'one', title: 'Compare two mixtures', type: 'quiz', content: 'Compare quantities using ratios.',
  key_points: [], actions: [{ role_id: 'adeline', text: 'What relationship do you notice?' }],
  learner_task: 'Explain your comparison.', success_criteria: ['Use multiplicative reasoning.'],
  family_roles: { elementary: 'Draw amounts.', middle: 'Compare ratios.', high_school: 'Justify scaling.' },
  question: { prompt: 'Which ratio equals 1:2?', choices: [{ id: 'a', label: '2:4' }, { id: 'b', label: '2:3' }] },
  simulation: null, materials: [], steps: [],
};
const state: ClassroomState = { phase: 'ready', title: 'Mixtures', classroom: {
  blueprint: { title: 'Mixtures', understanding: 'Ratios compare quantities.', essential_question: 'How can we compare mixtures?',
    demonstration: 'Explain a comparison.', integrated_tracks: ['APPLIED_MATHEMATICS'], next_revisit: 'Connect graphs.',
    roster: [{ id: 'adeline', name: 'Adeline', role: 'teacher', persona: 'Warm mentor.' }] },
  scenes: [scene, { ...scene, id: 'two', title: 'Apply it elsewhere' }],
} };

describe('Fresh classroom', () => {
  it('keeps a quiz answer on the page until it is saved and shows server feedback', async () => {
    mocks.submit.mockResolvedValue({ saved: true, correct: true, review: 'Both quantities doubled.' });
    render(<ClassroomPlayer state={state} studentId="child" itemId="unit" grade="8" />);
    expect(screen.getByText('Adeline')).toBeTruthy();
    expect(screen.queryByText('Both quantities doubled.')).toBeNull();
    fireEvent.click(screen.getByLabelText('2:4'));
    expect((screen.getByText('Next') as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByText('Check and save'));
    await waitFor(() => expect(screen.getByText(/Both quantities doubled/)).toBeTruthy());
    expect(mocks.submit).toHaveBeenCalledWith('child', 'unit', 'one', 'a', expect.any(String));
    expect((screen.getByText('Next') as HTMLButtonElement).disabled).toBe(false);
  });
  it('asks Adeline about the current scene and displays her saved answer', async () => {
    mocks.talk.mockResolvedValue({ key: 'q', question: 'Why multiply?', answer: 'Compare equal groups.', teaching_move: 'explain' });
    render(<ClassroomPlayer state={state} studentId="child" itemId="unit" grade="8" />);
    fireEvent.change(screen.getByLabelText('Talk it through with Adeline'), { target: { value: 'Why multiply?' } });
    fireEvent.click(screen.getByText('Send'));
    await waitFor(() => expect(screen.getByText('Compare equal groups.')).toBeTruthy());
    expect(mocks.talk).toHaveBeenCalledWith('child', 'unit', 'one', 'Why multiply?', expect.any(String));
  });
});
