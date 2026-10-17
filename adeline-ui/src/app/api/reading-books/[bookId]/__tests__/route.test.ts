import { afterEach, describe, expect, it, vi } from 'vitest';
import { CURATED_PUBLIC_DOMAIN_BOOKS } from '@/data/learningVault';
vi.mock('next/headers', () => ({ cookies: async () => ({ get: () => ({ value: 'test-session' }) }) }));
vi.mock('@/lib/server/brain-url', () => ({ resolveBrainBaseUrl: () => 'https://brain.example' }));
import { GET } from '../route';
afterEach(() => vi.unstubAllGlobals());
describe('book content proxy', () => {
  it('opens a classic after it was added under a database id', async () => {
    const classic = CURATED_PUBLIC_DOMAIN_BOOKS[0];
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(null, { status: 404 }))
      .mockResolvedValueOnce(Response.json({ title: classic.title, author: classic.author, source_url: null }))
      .mockResolvedValueOnce(new Response('PK-epub-data', { headers: { 'content-type': 'application/epub+zip' } }));
    vi.stubGlobal('fetch', fetchMock);
    const response = await GET(new Request('https://app.example/api/reading-books/database-id'), { params: Promise.resolve({ bookId: 'database-id' }) });
    expect(response.status).toBe(200);
    expect(await response.text()).toBe('PK-epub-data');
    expect(String(fetchMock.mock.calls[2][0])).toContain('gutenberg.org');
  });
});
