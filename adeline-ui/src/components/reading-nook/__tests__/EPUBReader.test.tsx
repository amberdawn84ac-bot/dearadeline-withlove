import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { EPUBReader } from '../EPUBReader';
import { ReaderProvider } from '@/lib/reader-context';

const epubMocks = vi.hoisted(() => ({
  open: vi.fn(), renderTarget: vi.fn(), generate: vi.fn(), destroy: vi.fn(), handlers: {} as Record<string, (arg: unknown) => void>,
}));

// Mock EPUB.js at top of file before describe block
vi.mock('epubjs', () => {
  const makeBook = () => ({
    open: epubMocks.open,
    destroy: epubMocks.destroy,
    renderTo: vi.fn((target: HTMLElement | null) => {
      if (!target) throw new Error('Reader container missing');
      epubMocks.renderTarget(target);
      return ({
      display: vi.fn().mockResolvedValue(undefined),
      prev: vi.fn().mockResolvedValue(undefined),
      next: vi.fn().mockResolvedValue(undefined),
      on: vi.fn((name: string, handler: (arg: unknown) => void) => { epubMocks.handlers[name] = handler; }),
      off: vi.fn(),
    }); }),
    spine: { get: vi.fn(() => ({ next: vi.fn(() => null) })) },
    locations: {
      generate: epubMocks.generate,
      percentageFromCfi: vi.fn(() => 0.5),
    },
    ready: Promise.resolve(),
    navigation: { toc: [] },
  });
  function EPub() {
    return makeBook();
  }
  return { default: EPub };
});

describe('EPUBReader', () => {
  const mockBook = {
    title: 'Test Book',
    author: 'Test Author',
    source_url: 'https://example.com/test.epub',
    lexile_level: 750,
    track: 'ENGLISH_LITERATURE',
    cover_url: 'https://example.com/cover.jpg',
  };

  const mockProps = {
    bookId: 'book-123',
    sessionId: 'session-123',
    studentId: 'student-123',
    book: mockBook,
    onComplete: vi.fn(),
    onBack: vi.fn(),
  };

  const renderReader = (props = mockProps) =>
    render(
      <ReaderProvider>
        <EPUBReader {...props} />
      </ReaderProvider>,
    );

  beforeEach(() => {
    vi.clearAllMocks();
    epubMocks.open.mockResolvedValue(undefined);
    epubMocks.generate.mockResolvedValue(undefined);

    // Mock fetch
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('renders loading state initially', () => {
    renderReader();
    expect(screen.getByText('Loading book...')).toBeInTheDocument();
  });

  it('displays close button and control bar', async () => {
    renderReader();

    await waitFor(() => {
      expect(screen.getByText('Close')).toBeInTheDocument();
    });
  });

  it('displays book metadata in sidebar', async () => {
    renderReader();

    await waitFor(() => {
      expect(screen.getByText('Test Book')).toBeInTheDocument();
      expect(screen.getByText('Test Author')).toBeInTheDocument();
    });
  });

  it('shows TOC button and can toggle TOC modal', async () => {
    renderReader();

    await waitFor(() => {
      const tocButton = screen.getByText('TOC');
      expect(tocButton).toBeInTheDocument();
    });
  });

  it('displays lexile level badge when provided', async () => {
    renderReader();

    await waitFor(() => {
      expect(screen.getByText('750L')).toBeInTheDocument();
    });
  });

  it('calls onBack when close button is clicked', async () => {
    renderReader();

    await waitFor(() => {
      const closeButton = screen.getByText('Close');
      fireEvent.click(closeButton);
      expect(mockProps.onBack).toHaveBeenCalled();
    });
  });

  it('displays progress percentage', async () => {
    renderReader();

    await waitFor(() => {
      // Progress should be displayed
      expect(screen.getByText(/complete/)).toBeInTheDocument();
    });
  });

  it('renders reading time component', async () => {
    renderReader();

    await waitFor(() => {
      expect(screen.getByText(/minutes reading time/)).toBeInTheDocument();
    });
  });

  it('opens extensionless proxy URLs as EPUB files in a mounted viewer', async () => {
    renderReader({ ...mockProps, book: { ...mockBook, source_url: '/api/reading-books/classic-1' } });
    await waitFor(() => expect(epubMocks.open).toHaveBeenCalledWith('/api/reading-books/classic-1', 'epub'));
    await waitFor(() => expect(epubMocks.renderTarget).toHaveBeenCalledWith(screen.getByTestId('epub-viewer')));
    await waitFor(() => expect(screen.queryByText('Loading book...')).not.toBeInTheDocument());
  });

  it('shows the book while the progress index is still building and destroys it on exit', async () => {
    epubMocks.generate.mockReturnValue(new Promise(() => {}));
    const view = renderReader();
    await waitFor(() => expect(epubMocks.generate).toHaveBeenCalled());
    expect(screen.queryByText('Loading book...')).not.toBeInTheDocument();
    view.unmount();
    expect(epubMocks.destroy).toHaveBeenCalledOnce();
  });

  it('uses the EPUB location API without crashing on the first page', async () => {
    renderReader();
    await waitFor(() => expect(epubMocks.renderTarget).toHaveBeenCalled());
    expect(() => epubMocks.handlers.relocated({ start: { cfi: 'epubcfi(test)', href: 'chapter.xhtml' }, atEnd: false })).not.toThrow();
    expect(await screen.findByText('50% complete')).toBeInTheDocument();
  });

  it('handles error state gracefully', async () => {
    epubMocks.open.mockRejectedValueOnce(new Error('Readable edition unavailable'));
    renderReader();
    expect(await screen.findByText('Back to Shelf')).toBeInTheDocument();
    expect(screen.getByText('Readable edition unavailable')).toBeInTheDocument();
  });
});
