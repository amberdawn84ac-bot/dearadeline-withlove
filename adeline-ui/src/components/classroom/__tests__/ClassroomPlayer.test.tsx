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
        { role_id: 'adeline', text: scene.content, focus: 'content' },
        { role_id: 'helper', text: 'Which quantities would you compare?' },
      ] }],
    } };
    render(<ClassroomPlayer state={narratedState} studentId="child" itemId="unit" grade="8" />);
    expect(screen.getAllByText(scene.content)).toHaveLength(1);
    expect(screen.getByText('Which quantities would you compare?')).toBeInTheDocument();
    expect(screen.getByLabelText('Talk it through with Adeline')).toBeInTheDocument();
    fireEvent.click(await screen.findByText('Listen'));
    expect(speak).toHaveBeenCalledWith(expect.objectContaining({ text: scene.content }));
    const utterance = speak.mock.calls[0][0];
    const { act } = await import('@testing-library/react');
    act(() => utterance.onstart());
    expect(screen.getByText(scene.content).className).toContain('ring-2');
    act(() => utterance.onend());
    expect(screen.getByText(scene.content).className).not.toContain('ring-2');
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
  it('saves sorting choices, shows feedback only after submission, and restores choices after reopening', async () => {
    const sorting = { instruction: 'Sort these samples.', categories: [{ id: 'solid', label: 'Solid' }, { id: 'liquid', label: 'Liquid' }], items: [{ id: 'rock', label: 'Rock' }, { id: 'water', label: 'Water' }] };
    const sortingState: ClassroomState = { ...state, classroom: { ...state.classroom!, scenes: [{ ...scene, type: 'interactive', question: null, sorting }, state.classroom!.scenes[1]] } };
    mocks.submit.mockResolvedValue({ saved: true, correct: true, review: '2 of 2 classifications match.', items: [{ item_id: 'rock', correct: true, explanation: 'The rock retains its shape.' }] });
    const view = render(<ClassroomPlayer state={sortingState} studentId="child" itemId="unit" grade="3" />);
    expect(screen.queryByText(/retains its shape/)).not.toBeInTheDocument();
    expect(screen.getByText('Check and save')).toBeDisabled();
    fireEvent.change(screen.getByLabelText('Category for Rock'), { target: { value: 'solid' } });
    expect(screen.getByText('Check and save')).toBeDisabled();
    expect(screen.getByText('Next')).toBeDisabled();
    fireEvent.change(screen.getByLabelText('Category for Water'), { target: { value: 'liquid' } });
    fireEvent.click(screen.getByText('Check and save'));
    await screen.findByText(/retains its shape/);
    expect(mocks.submit).toHaveBeenLastCalledWith('child', 'unit', 'one', '{"rock":"solid","water":"liquid"}', expect.any(String));
    fireEvent.click(screen.getByText('Next'));
    fireEvent.click(screen.getByText('Previous'));
    expect(screen.getByLabelText('Category for Rock')).toHaveValue('solid');
    view.unmount();
    render(<ClassroomPlayer state={{ ...sortingState, responses: { one: { text: '{"rock":"solid","water":"liquid"}', feedback: { saved: true, review: 'Saved.' } } } }} studentId="child" itemId="unit" grade="3" />);
    await waitFor(() => expect(screen.getByLabelText('Category for Water')).toHaveValue('liquid'));
  });
  it('requests a small hint through the saved coaching conversation', async () => {
    mocks.talk.mockResolvedValue({ key: 'hint', question: 'A hint', answer: 'Try comparing equal groups in another example.', teaching_move: 'scaffold' });
    render(<ClassroomPlayer state={state} studentId="child" itemId="unit" grade="8" />);
    fireEvent.click(screen.getByText('Give me a hint'));
    await screen.findByText('Try comparing equal groups in another example.');
    expect(mocks.talk).toHaveBeenLastCalledWith('child', 'unit', 'one', expect.stringContaining('different example'), expect.any(String));
  });

  it('saves a prediction before showing the lab and protects unsaved model changes during navigation', async () => {
    mocks.submit.mockResolvedValue({ saved: true, review: 'Saved.' });
    const labState: ClassroomState = { ...state, classroom: { ...state.classroom!, scenes: [{ ...scene, question: null, type: 'interactive', interaction: { kind: 'water_heating', prediction_prompt: 'What will change?', observation_prompt: 'Explain your result.', nodes: [], edges: [], formula: 'H2O' } }, state.classroom!.scenes[1]] } };
    render(<ClassroomPlayer state={labState} studentId="child" itemId="unit" grade="8" />);
    fireEvent.change(screen.getByLabelText('Your prediction'), { target: { value: 'The temperature will rise.' } });
    expect(screen.getByText('Next')).toBeDisabled();
    fireEvent.click(screen.getByText('Save prediction and explore'));
    await screen.findByLabelText('Energy added');
    expect(mocks.submit).toHaveBeenLastCalledWith('child', 'unit', 'one', 'The temperature will rise.', expect.any(String), expect.objectContaining({ stage: 'prediction' }));
    fireEvent.change(screen.getByLabelText('Energy added'), { target: { value: '20.9' } });
    expect(screen.getByText('Next')).toBeDisabled();
    fireEvent.click(screen.getByText('Record this result'));
    fireEvent.change(screen.getByLabelText('Your observations'), { target: { value: 'Energy changed the phase while temperature stayed zero.' } });
    fireEvent.click(screen.getByText('Save observations and results'));
    await waitFor(() => expect(screen.getByText('Next')).not.toBeDisabled());
    fireEvent.click(screen.getByText('Next')); fireEvent.click(screen.getByText('Previous'));
    expect(screen.getByLabelText('Energy added')).toHaveValue('20.9');
    expect(screen.getByLabelText('Your observations')).toHaveValue('Energy changed the phase while temperature stayed zero.');
  });
  it('pauses after each narration part and offers learner-controlled continuation', async () => {
    const speak = vi.fn(), pause = vi.fn(), resume = vi.fn();
    vi.stubGlobal('speechSynthesis', { cancel: vi.fn(), speak, pause, resume });
    vi.stubGlobal('SpeechSynthesisUtterance', class { constructor(public text: string) {} });
    const pages = { ...state, classroom: { ...state.classroom!, scenes: [{ ...scene, actions: [{ role_id: 'adeline', text: 'First, make a prediction.' }, { role_id: 'adeline', text: 'Now inspect the result.' }] }] } };
    render(<ClassroomPlayer state={pages} studentId="child" itemId="unit" grade="8" />);
    fireEvent.click(await screen.findByText('Listen'));
    expect(speak).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByText('Pause narration')); expect(pause).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByText('Resume narration')); expect(resume).toHaveBeenCalledTimes(1);
    const { act } = await import('@testing-library/react');
    act(() => speak.mock.calls[0][0].onend());
    expect(speak).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByText('Continue narration'));
    expect(speak).toHaveBeenLastCalledWith(expect.objectContaining({ text: 'Now inspect the result.' }));
  });

});
