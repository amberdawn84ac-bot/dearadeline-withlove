import { describe, expect, it, vi } from 'vitest';
const { redirect } = vi.hoisted(() => ({ redirect: vi.fn() }));
vi.mock('next/navigation', () => ({ redirect }));
import ReaderPage from '../page';

describe('saved reader links', () => {
  it('uses the curated-aware dashboard reader for the gardening book', async () => {
    await ReaderPage({ params: Promise.resolve({ bookId: 'childrens-gardening' }) });
    expect(redirect).toHaveBeenCalledWith('/dashboard/reading-nook/childrens-gardening');
  });
});
