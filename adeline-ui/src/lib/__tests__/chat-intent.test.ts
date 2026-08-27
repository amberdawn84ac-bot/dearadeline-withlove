import { describe, expect, it } from 'vitest';

import { isCompletedActivityReport, isExplicitLearningRequest } from '@/lib/chat-intent';

describe('Adeline chat intent', () => {
  it('treats a request to learn about cancer as teaching, not activity credit', () => {
    const message = 'I want to learn about cancer. I read six kids have got Ewing sarcoma in Ladera Ranch.';

    expect(isExplicitLearningRequest(message)).toBe(true);
    expect(isCompletedActivityReport(message)).toBe(false);
  });

  it('does not treat a reported fact beginning with "I read" as completed schoolwork', () => {
    expect(isCompletedActivityReport('I read six kids have Ewing sarcoma in Ladera Ranch.')).toBe(false);
  });

  it('still recognizes real completed work and completed reading', () => {
    expect(isCompletedActivityReport('I baked bread and compared how the dough rose.')).toBe(true);
    expect(isCompletedActivityReport('I read a chapter of my biology textbook.')).toBe(true);
  });
});
