import { CURATED_PUBLIC_DOMAIN_BOOKS, type LibraryBook } from '@/data/learningVault';

export function gutenbergIdFromUrl(url: string | undefined): string | null {
  if (!url) return null;
  const match = url.match(/gutenberg\.org\/(?:ebooks|cache\/epub)\/(\d+)/i);
  return match?.[1] ?? null;
}

export function gutenbergEpubUrls(gutenbergId: string): string[] {
  return [
    `https://www.gutenberg.org/ebooks/${gutenbergId}.epub.images`,
    `https://www.gutenberg.org/ebooks/${gutenbergId}.epub.noimages`,
    `https://www.gutenberg.org/cache/epub/${gutenbergId}/pg${gutenbergId}-images-3.epub`,
    `https://www.gutenberg.org/cache/epub/${gutenbergId}/pg${gutenbergId}-images.epub`,
  ];
}

export function epubUrlsFromSource(sourceUrl: string): string[] {
  const gutenbergId = gutenbergIdFromUrl(sourceUrl);
  if (gutenbergId) return gutenbergEpubUrls(gutenbergId);
  if (/\.epub(\b|$)/i.test(sourceUrl)) return [sourceUrl];
  return [];
}

export function findCuratedBook(bookId: string): LibraryBook | undefined {
  return CURATED_PUBLIC_DOMAIN_BOOKS.find((book) => book.id === bookId);
}

export function curatedBookAsReaderData(book: LibraryBook) {
  return {
    id: book.id,
    title: book.title,
    author: book.author,
    description: book.description,
    track: 'ENGLISH_LITERATURE',
    source_url: `/api/reading-books/${encodeURIComponent(book.id)}`,
    source_library: 'Project Gutenberg',
    html_url: book.readingUrl,
  };
}
