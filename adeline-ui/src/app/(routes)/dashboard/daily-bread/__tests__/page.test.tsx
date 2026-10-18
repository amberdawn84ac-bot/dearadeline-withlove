import { render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import DailyBreadLessonPage from '../page';
vi.mock('@/lib/useStudent', () => {
  const student = { id: 'child', gradeLevel: '8' };
  return { useStudent: () => ({ student }) };
});
afterEach(() => vi.unstubAllGlobals());
const daily = { lessonTitle: 'A psalm of creation', bigIdea: 'Look closely at the text.', reference: 'Psalms 19:2', verse: 'The heavens recount the glory of El.', original: 'El', originalMeaning: 'God', context: 'A psalm.', readTogether: [], familyDiscussion: [], creditConnections: [], portfolioEvidence: [] };
function respond(sections: Array<{heading: string; content: string}>) {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(Response.json(daily)).mockResolvedValueOnce(Response.json({ is_fox: false, sections })));
}
describe('Daily Bread study sections', () => {
  it('hides old instruction fallback and empty sections while retaining the passage', async () => {
    respond([{ heading: 'Translation and Textual History', content: 'Compare named translations with the source wording. Record only documented variants or changes; label disputed claims and unknown motives honestly.' }, { heading: 'Empty study', content: ' ' }, { heading: 'Source wording', content: 'The supplied source uses El.' }]);
    render(<DailyBreadLessonPage />);
    expect(await screen.findByText('A psalm of creation')).toBeInTheDocument();
    await screen.findByText('The supplied source uses El.');
    expect(screen.queryByText('Translation and Textual History')).not.toBeInTheDocument();
    expect(screen.queryByText(/Compare named translations/)).not.toBeInTheDocument();
    expect(screen.queryByText('Empty study')).not.toBeInTheDocument();
  });
  it('shows the actual completed translation comparison', async () => {
    const content = 'The Hebrew uses El; the supplied English translation renders it as God.';
    respond([{ heading: 'Translation and Textual History', content }]);
    render(<DailyBreadLessonPage />);
    expect(await screen.findByText(content)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Translation and Textual History' })).toBeInTheDocument();
  });
});
