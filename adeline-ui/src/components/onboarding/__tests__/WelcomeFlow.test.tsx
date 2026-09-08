import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { WelcomeFlow } from '../WelcomeFlow';

describe('WelcomeFlow', () => {
  it('requires parent consent before moving past the COPPA step', async () => {
    const user = userEvent.setup();
    render(<WelcomeFlow onComplete={vi.fn()} />);

    expect(screen.getByText('Welcome, Parents & Learners!')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /next/i }));
    expect(screen.getByText('Parent/Guardian Information')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /next/i }));
    expect(screen.getByText('Parent/guardian name is required')).toBeInTheDocument();
    expect(screen.getByText('A valid parent/guardian email is required')).toBeInTheDocument();
    expect(screen.getByText('Please check the box to provide consent')).toBeInTheDocument();
  });

  it('completes onboarding with parent, learner, and coverage details', async () => {
    const onComplete = vi.fn();
    const user = userEvent.setup();
    render(<WelcomeFlow onComplete={onComplete} />);

    await user.click(screen.getByRole('button', { name: /next/i }));
    await user.type(screen.getByPlaceholderText('e.g., Sarah Johnson'), 'Pat Parent');
    await user.type(screen.getByPlaceholderText('parent@example.com'), 'pat@example.com');
    await user.click(screen.getByRole('checkbox'));
    await user.click(screen.getByRole('button', { name: /next/i }));

    await user.type(screen.getByPlaceholderText('e.g., Emma Johnson'), 'Emma Johnson');
    await user.click(screen.getByRole('button', { name: '5' }));
    await user.click(screen.getByRole('button', { name: 'Science' }));
    await user.click(screen.getByRole('button', { name: /next/i }));

    const [stateSelect, yearSelect] = screen.getAllByRole('combobox');
    await user.selectOptions(stateSelect, 'Oklahoma');
    await user.selectOptions(yearSelect, '2030');
    await user.click(screen.getByRole('button', { name: /complete setup/i }));

    expect(onComplete).toHaveBeenCalledWith({
      name: 'Emma Johnson',
      gradeLevel: '5',
      interests: ['Science'],
      learningStyle: 'EXPEDITION',
      state: 'Oklahoma',
      targetGraduationYear: 2030,
      coppaConsent: true,
      parentName: 'Pat Parent',
      parentEmail: 'pat@example.com',
    });
  });
});
