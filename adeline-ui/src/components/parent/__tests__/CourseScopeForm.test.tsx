import { render,screen,waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe,it,expect,vi } from 'vitest';
import CourseScopeForm from '../CourseScopeForm';
import { defineCourseScope,getCourseTargets } from '@/lib/brain-client';
vi.mock('@/lib/brain-client',()=>({defineCourseScope:vi.fn(),getCourseTargets:vi.fn()}));
vi.mock('@/lib/classroom-client',()=>({TRACKS:{CREATION_SCIENCE:'Science'}}));
describe('course scope',()=>{
  it('requires selected objectives and a rationale before saving the explicit allocation',async()=>{
    vi.mocked(getCourseTargets).mockResolvedValue([{id:'mass-1',title:'Conservation of mass',status:'demonstrated'}]);
    vi.mocked(defineCourseScope).mockResolvedValue({id:'scope'});
    const saved=vi.fn();
    render(<CourseScopeForm studentId="child" onSaved={saved}/>);
    await userEvent.click(screen.getByText('Define a course for credit review'));
    expect(screen.getByRole('button',{name:'Save course scope'})).toBeDisabled();
    await userEvent.type(screen.getByLabelText('Course title'),'Physical Science');
    await userEvent.click(await screen.findByRole('checkbox'));
    expect(screen.getByRole('button',{name:'Save course scope'})).toBeDisabled();
    await userEvent.type(screen.getByLabelText('Why does this scope warrant these credits?'),'This scope covers the planned course objectives with independent projects and explanations.');
    await userEvent.click(screen.getByRole('button',{name:'Save course scope'}));
    await waitFor(()=>expect(saved).toHaveBeenCalledOnce());
    expect(defineCourseScope).toHaveBeenCalledWith('child',expect.objectContaining({skill_ids:['mass-1'],bucket:'SCIENCE_CORE',credit_units:.5}));
  });
});
