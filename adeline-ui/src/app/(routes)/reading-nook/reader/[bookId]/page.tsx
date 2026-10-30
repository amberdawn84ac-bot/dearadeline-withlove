import { redirect } from 'next/navigation';

// Keep saved links working through the same reader as the dashboard. That
// reader resolves curated public-domain IDs before requiring a database book.
export default async function ReaderPage({ params }: { params: Promise<{ bookId: string }> }) {
  const { bookId } = await params;
  redirect(`/dashboard/reading-nook/${encodeURIComponent(bookId)}`);
}
