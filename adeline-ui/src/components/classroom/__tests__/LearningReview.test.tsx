import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import LearningReview from '../LearningReview';
import { reviewClassroomResponse } from '@/lib/classroom-client';
vi.mock('@/lib/classroom-client', () => ({ reviewClassroomResponse: vi.fn() }));
describe('learning review', () => {
  it('keeps saved work distinct from an unavailable assessment and allows retry', async () => {
    vi.mocked(reviewClassroomResponse).mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce({ status:'unmapped', findings:[], message:'A parent can link your target.' });
    render(<LearningReview feedback={{saved:true,review:'Saved',submission_key:'work-123'}} studentId="child" itemId="lesson" track="CREATION_SCIENCE" />);
    await userEvent.click(screen.getByRole('button',{name:'Review my saved work'}));
    expect(await screen.findByRole('alert')).toHaveTextContent('Your work is saved');
    await userEvent.click(screen.getByRole('button',{name:'Review my saved work'}));
    expect(await screen.findByText('A parent can link your target.')).toBeInTheDocument();
  });
  it('routes a diagnosed gap into practice with the exact target', () => {
    render(<LearningReview feedback={{saved:true,review:'Saved',assessment:{status:'reviewed',message:'Reviewed',findings:[{skill_id:'mass',result:'developing',evidence_quote:'It vanished',reasoning:'Gas left the open system.',next_step:'Compare the gas and scale masses.'}]}}} studentId="child" itemId="lesson" track="CREATION_SCIENCE" />);
    expect(screen.getByRole('link',{name:'Practice this next'})).toHaveAttribute('href',expect.stringContaining('target=mass'));
    expect(screen.getByText('Keep working on this')).toBeInTheDocument();
  });
});
