import { describe, expect, it } from 'vitest';
import {
  curatedBookAsReaderData,
  epubUrlsFromSource,
  findCuratedBook,
  gutenbergIdFromUrl,
} from '@/lib/public-domain-books';

describe('public-domain books', () => {
  it('pulls a Gutenberg id from the catalog URL', () => {
    expect(gutenbergIdFromUrl('https://www.gutenberg.org/ebooks/47616')).toBe('47616');
  });

  it('turns a Gutenberg page into EPUB download URLs', () => {
    const urls = epubUrlsFromSource('https://www.gutenberg.org/ebooks/47616');
    expect(urls[0]).toBe('https://www.gutenberg.org/ebooks/47616.epub.images');
    expect(urls.some((url) => url.endsWith('.epub'))).toBe(true);
  });

  it('exposes curated classics for in-app reading', () => {
    const book = findCuratedBook('plants-and-their-children');
    expect(book?.title).toMatch(/Plants and Their Children/);
    expect(curatedBookAsReaderData(book!).source_url).toContain('plants-and-their-children');
  });
});
