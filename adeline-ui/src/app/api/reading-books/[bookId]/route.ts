import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';
import { resolveBrainBaseUrl } from '@/lib/server/brain-url';
import { epubUrlsFromSource, findCuratedBook } from '@/lib/public-domain-books';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

const BRAIN_URL = resolveBrainBaseUrl();

const ALLOWED_BOOK_HOSTS = new Set([
  'www.gutenberg.org',
  'gutenberg.org',
  'standardebooks.org',
  'www.standardebooks.org',
]);

function allowedEpubUrl(raw: string): URL | null {
  try {
    const source = new URL(raw);
    if (source.protocol !== 'https:' || !ALLOWED_BOOK_HOSTS.has(source.hostname)) return null;
    return source;
  } catch {
    return null;
  }
}

async function fetchFirstEpub(urls: string[]): Promise<Response | null> {
  for (const url of urls) {
    const allowed = allowedEpubUrl(url);
    if (!allowed) continue;
    const response = await fetch(allowed, { redirect: 'follow', cache: 'force-cache' });
    const contentType = response.headers.get('content-type') || '';
    if (response.ok && response.body && !contentType.includes('text/html')) {
      return response;
    }
  }
  return null;
}

function epubResponse(body: ReadableStream<Uint8Array> | ArrayBuffer, title: string, cache: string) {
  const filename = `${title.replace(/[^a-z0-9]+/gi, '-').toLowerCase() || 'book'}.epub`;
  return new Response(body, {
    headers: {
      'Content-Type': 'application/epub+zip',
      'Cache-Control': cache,
      'Content-Disposition': `inline; filename="${filename}"`,
    },
  });
}

export async function GET(
  _request: Request,
  context: { params: Promise<{ bookId: string }> },
) {
  const { bookId } = await context.params;
  const token = (await cookies()).get('auth_token')?.value;
  if (!token) return NextResponse.json({ message: 'Sign in required' }, { status: 401 });

  const storedResponse = await fetch(
    `${BRAIN_URL}/brain/bookshelf/${encodeURIComponent(bookId)}/download`,
    { headers: { authorization: `Bearer ${token}` }, cache: 'no-store' },
  );
  if (storedResponse.ok && storedResponse.body) {
    return epubResponse(storedResponse.body, 'book', 'private, max-age=3600');
  }

  const curated = findCuratedBook(bookId);
  if (curated) {
    const epub = await fetchFirstEpub(epubUrlsFromSource(curated.sourceUrl));
    if (epub?.body) return epubResponse(epub.body, curated.title, 'public, max-age=86400, s-maxage=604800');
  }

  const metadataResponse = await fetch(
    `${BRAIN_URL}/brain/api/books/${encodeURIComponent(bookId)}`,
    { headers: { authorization: `Bearer ${token}` }, cache: 'no-store' },
  );
  if (!metadataResponse.ok) {
    return NextResponse.json({ message: 'Book not found' }, { status: metadataResponse.status });
  }

  const book = (await metadataResponse.json()) as { source_url?: string; title?: string };
  const epub = await fetchFirstEpub(epubUrlsFromSource(book.source_url || ''));
  if (epub?.body) {
    return epubResponse(epub.body, book.title || 'book', 'public, max-age=86400, s-maxage=604800');
  }

  return NextResponse.json({ message: 'Readable edition unavailable' }, { status: 404 });
}
