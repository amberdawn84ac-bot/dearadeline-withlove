import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {beforeEach,describe,expect,it,vi} from 'vitest';
import {FamilyUnitComposer} from '../FamilyUnitComposer';
import {enqueueFamilyUnit} from '@/lib/curriculum-client';
vi.mock('@/lib/curriculum-client',()=>({enqueueFamilyUnit:vi.fn()}));

describe('multi-experience family unit',()=>{
  beforeEach(()=>vi.clearAllMocks());
  it('queues experiences in parent order while keeping their subjects',async()=>{
    vi.mocked(enqueueFamilyUnit).mockResolvedValue({});
    const onChange=vi.fn();
    render(<FamilyUnitComposer householdId="family" tracks={{CREATION_SCIENCE:'Science',TRUTH_HISTORY:'History'}} onChange={onChange}/>);
    fireEvent.change(screen.getByLabelText('Unit title'),{target:{value:'The Farm'}});
    fireEvent.change(screen.getByLabelText('Experience 1'),{target:{value:'Test the soil'}});
    fireEvent.click(screen.getByText('Add experience'));
    fireEvent.change(screen.getByLabelText('Experience 2'),{target:{value:'Who owned this land?'}});
    fireEvent.change(screen.getAllByLabelText('Primary area')[1],{target:{value:'TRUTH_HISTORY'}});
    fireEvent.click(screen.getByText('Queue unit'));
    await waitFor(()=>expect(enqueueFamilyUnit).toHaveBeenCalledWith('family','The Farm',[
      {canonical_topic:'Test the soil',track:'CREATION_SCIENCE'},
      {canonical_topic:'Who owned this land?',track:'TRUTH_HISTORY'},
    ]));
    await waitFor(()=>expect(onChange).toHaveBeenCalledOnce());
  });
  it('preserves the parent plan when queuing fails',async()=>{
    vi.mocked(enqueueFamilyUnit).mockRejectedValue(new Error('offline'));
    render(<FamilyUnitComposer householdId="family" tracks={{CREATION_SCIENCE:'Science'}} onChange={vi.fn()}/>);
    fireEvent.change(screen.getByLabelText('Unit title'),{target:{value:'Water'}});
    fireEvent.change(screen.getByLabelText('Experience 1'),{target:{value:'Measure runoff'}});
    fireEvent.click(screen.getByText('Queue unit'));
    await screen.findByRole('alert');
    expect(screen.getByLabelText('Unit title')).toHaveValue('Water');
    expect(screen.getByLabelText('Experience 1')).toHaveValue('Measure runoff');
  });
});
