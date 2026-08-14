import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

const BRAIN_URL = (
  process.env.BRAIN_INTERNAL_URL ||
  process.env.BRAIN_URL ||
  process.env.NEXT_PUBLIC_BRAIN_URL ||
  'https://dearadeline-withlove-production.up.railway.app'
).replace(/\/$/, '');

const ALLOWED_BOOK_HOSTS = new Set(['www.gutenberg.org', 'gutenberg.org']);

export async function GET(
  _request: Request,
  context: { params: Promise<{ bookId: string }> },
) {
  const { bookId } = await context.params;
  const token = (await cookies()).get('auth_token')?.value;
  if (!token) return NextResponse.json({ message: 'Sign in required' }, { status: 401 });

  // Books found through Search & Add are downloaded by the backend's
  // Standard Ebooks → Gutenberg waterfall and stored as a safe EPUB copy.
  const storedResponse = await fetch(
    `${BRAIN_URL}/brain/bookshelf/${encodeURIComponent(bookId)}/download`,
    { headers: { authorization: `Bearer ${token}` }, cache: 'no-store' },
  );
  if (storedResponse.ok && storedResponse.body) {
    return new Response(storedResponse.body, {
      headers: {
        'Content-Type': 'application/epub+zip',
        'Cache-Control': 'private, max-age=3600',
        'Content-Disposition': 'inline; filename="book.epub"',
      },
    });
  }

  const metadataResponse = await fetch(
    `${BRAIN_URL}/brain/api/books/${encodeURIComponent(bookId)}`,
    { headers: { authorization: `Bearer ${token}` }, cache: 'no-store' },
  );
  if (!metadataResponse.ok) {
    return NextResponse.json({ message: 'Book not found' }, { status: metadataResponse.status });
  }

  const book = (await metadataResponse.json()) as { source_url?: string; title?: string };
  if (!book.source_url) {
    return NextResponse.json({ message: 'Readable edition unavailable' }, { status: 404 });
  }

  const source = new URL(book.source_url);
  if (source.protocol !== 'https:' || !ALLOWED_BOOK_HOSTS.has(source.hostname)) {
    return NextResponse.json({ message: 'Unsupported book source' }, { status: 422 });
  }

  const epubResponse = await fetch(source, { redirect: 'follow', cache: 'force-cache' });
  if (!epubResponse.ok || !epubResponse.body) {
    return NextResponse.json({ message: 'Edition is temporarily unavailable' }, { status: 502 });
  }

  return new Response(epubResponse.body, {
    headers: {
      'Content-Type': 'application/epub+zip',
      'Cache-Control': 'public, max-age=86400, s-maxage=604800',
      'Content-Disposition': `inline; filename="${(book.title || 'book').replace(/[^a-z0-9]+/gi, '-').toLowerCase()}.epub"`,
    },
  });
}
