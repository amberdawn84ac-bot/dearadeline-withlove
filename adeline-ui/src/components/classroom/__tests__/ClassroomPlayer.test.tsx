import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import ClassroomPlayer from '../ClassroomPlayer';
import type { ClassroomScene, ClassroomState } from '@/lib/classroom-client';
const mocks = vi.hoisted(() => ({ submit: vi.fn(), talk: vi.fn(), materials: vi.fn() }));
vi.mock('@/lib/classroom-client', () => ({ submitClassroomResponse: mocks.submit, talkToClassroom: mocks.talk, getSceneMaterials: mocks.materials }));
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
  afterEach(() => vi.unstubAllGlobals());
  it('shows the lesson once while preserving spoken narration and distinct assistant dialogue', async () => {
    const speak = vi.fn();
    vi.stubGlobal('speechSynthesis', { cancel: vi.fn(), speak });
    vi.stubGlobal('SpeechSynthesisUtterance', class { constructor(public text: string) {} });
    const narratedState: ClassroomState = { ...state, classroom: {
      ...state.classroom!,
      blueprint: { ...state.classroom!.blueprint, roster: [
        ...state.classroom!.blueprint.roster,
        { id: 'helper', name: 'Research partner', role: 'assistant', persona: 'Asks focused questions.' },
      ] },
      scenes: [{ ...scene, actions: [
        { role_id: 'adeline', text: scene.content },
        { role_id: 'helper', text: 'Which quantities would you compare?' },
      ] }],
    } };
    render(<ClassroomPlayer state={narratedState} studentId="child" itemId="unit" grade="8" />);
    expect(screen.getAllByText(scene.content)).toHaveLength(1);
    expect(screen.getByText('Which quantities would you compare?')).toBeInTheDocument();
    expect(screen.getByLabelText('Talk it through with Adeline')).toBeInTheDocument();
    fireEvent.click(await screen.findByText('Listen'));
    expect(speak).toHaveBeenCalledWith(expect.objectContaining({ text: scene.content }));
  });
  it('shows attached book and map resources on their own page only', async () => {
    const pages: ClassroomState = { ...state, classroom: { ...state.classroom!, scenes: [
      { ...scene, resources: [
        { id: 'book', kind: 'link', title: 'Read Julius Caesar', url: 'https://www.gutenberg.org/ebooks/1120' },
        { id: 'map', kind: 'image', title: 'Roman Republic in 44 BCE', url: 'https://commons.wikimedia.org/wiki/File:map.svg', image_url: 'https://upload.wikimedia.org/map.svg', attribution: 'Map author' },
      ] },
      { ...scene, id: 'two', title: 'New question', resources: [] },
    ] } };
    render(<ClassroomPlayer state={pages} studentId="child" itemId="unit" grade="8" />);
    expect(screen.getByRole('img', { name: 'Roman Republic in 44 BCE' })).toHaveAttribute('src', 'https://upload.wikimedia.org/map.svg');
    expect(screen.getByText(/Open the reading or source/)).toHaveAttribute('href', 'https://www.gutenberg.org/ebooks/1120');
    fireEvent.click(screen.getByText('Next'));
    expect(screen.getByText('New question')).toBeInTheDocument();
    expect(screen.queryByRole('img', { name: 'Roman Republic in 44 BCE' })).not.toBeInTheDocument();
  });
  it('loads actual promised examples and keeps a slow response on its original page', async () => {
    let deliver!: (value: unknown) => void;
    mocks.materials.mockReturnValueOnce(new Promise(resolve => { deliver = resolve; }));
    const pages: ClassroomState = { ...state, classroom: { ...state.classroom!, blueprint: {
      ...state.classroom!.blueprint, roster: [...state.classroom!.blueprint.roster, { id: 'elara', name: 'Elara', role: 'assistant', persona: 'Provides examples.' }],
    }, scenes: [
      { ...scene, actions: [{ role_id: 'elara', text: "I've prepared examples of each rhetorical appeal." }] },
      { ...scene, id: 'two', title: 'New question' },
    ] } };
    render(<ClassroomPlayer state={pages} studentId="child" itemId="unit" grade="8" />);
    await waitFor(() => expect(mocks.materials).toHaveBeenCalledWith('child', 'unit', 'one'));
    fireEvent.click(screen.getByText('Next'));
    deliver([{ id: 'ethos', kind: 'text', title: 'Ethos example', content: 'A builder explains how their experience helps evaluate a foundation.' }]);
    expect(screen.queryByText('Ethos example')).not.toBeInTheDocument();
    fireEvent.click(screen.getByText('Previous'));
    expect(await screen.findByText('Ethos example')).toBeInTheDocument();
  });
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
