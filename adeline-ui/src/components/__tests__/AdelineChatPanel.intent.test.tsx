import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const mocks = vi.hoisted(() => ({
  reportActivity: vi.fn(),
  streamConversation: vi.fn(),
}));

vi.mock('@/lib/brain-client', () => ({
  scaffold: vi.fn(),
  listProjects: vi.fn(),
  getProject: vi.fn(),
  reportActivity: mocks.reportActivity,
  streamConversation: mocks.streamConversation,
  uploadActivityEvidence: vi.fn(),
}));

vi.mock('@/hooks/useALUStream', () => ({
  useALUStream: () => ({
    components: {},
    componentOrder: [],
    remediations: {},
    statusMessage: null,
    triggerRemediation: vi.fn(),
  }),
}));

import { AdelineChatPanel } from '@/components/AdelineChatPanel';

describe('AdelineChatPanel teaching intent', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Element.prototype.scrollIntoView = vi.fn();
    mocks.streamConversation.mockImplementation(async function* () {
      yield { type: 'text', delta: 'Cancer begins when changes in a cell disrupt its normal controls.' };
      yield { type: 'done' };
    });
  });

  it('sends the cancer request to the teaching conversation instead of activity reporting', async () => {
    render(<AdelineChatPanel studentId="student-1" gradeLevel="8" />);

    const input = screen.getByPlaceholderText('Ask Adeline or enter a topic…');
    fireEvent.change(input, {
      target: { value: 'I want to learn about cancer. I read six kids have got Ewing sarcoma in Ladera Ranch.' },
    });
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

    await waitFor(() => expect(mocks.streamConversation).toHaveBeenCalledOnce());
    expect(mocks.reportActivity).not.toHaveBeenCalled();
    expect(await screen.findByText(/Cancer begins when changes in a cell/)).toBeInTheDocument();
  });
});
