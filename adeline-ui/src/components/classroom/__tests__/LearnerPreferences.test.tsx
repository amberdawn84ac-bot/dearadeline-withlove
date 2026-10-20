import { useState } from 'react';
import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import LearnerPreferences from '../LearnerPreferences';
import type { LearnerContext } from '@/lib/classroom-client';

function Harness() {
  const [context, setContext] = useState<LearnerContext | undefined>();
  return <><LearnerPreferences value={context} onChange={setContext} /><output aria-label="Selected context">{JSON.stringify(context ?? null)}</output></>;
}
const selected = () => JSON.parse(screen.getByLabelText('Selected context').textContent!);

describe('LearnerPreferences', () => {
  it('keeps legacy input until an explicit choice and clears family grades when switching', async () => {
    const user = userEvent.setup();
    render(<Harness />);
    expect(selected()).toBeNull();
    await user.click(screen.getByText('Adjust learning preferences'));
    await user.selectOptions(screen.getByLabelText('Who is exploring?'), 'family');
    await user.click(screen.getByLabelText('3', { exact: true }));
    await user.click(screen.getByLabelText('8', { exact: true }));
    expect(selected().declared_grades).toEqual(['3', '8']);
    await user.selectOptions(screen.getByLabelText('Who is exploring?'), 'individual');
    expect(selected().declared_grades).toEqual([]);
    expect(selected().working_grade).toBeNull();
    await user.selectOptions(screen.getByLabelText('Who is exploring?'), '');
    expect(selected()).toBeNull();
  });

  it('keeps declared and working grade separate and sends functional preferences', async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await user.click(screen.getByText('Adjust learning preferences'));
    await user.selectOptions(screen.getByLabelText('Who is exploring?'), 'individual');
    await user.selectOptions(screen.getByLabelText('Declared grade'), '8');
    await user.selectOptions(screen.getByLabelText('Working grade for this topic'), '3');
    await user.click(screen.getByLabelText('More reading support'));
    await user.selectOptions(screen.getByLabelText('Time available'), '30');
    expect(selected()).toMatchObject({ mode: 'individual', declared_grades: ['8'], working_grade: '3', supports: ['reading_support'], minutes: 30 });
  });
});
