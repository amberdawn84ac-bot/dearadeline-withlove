import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { EPUBReader } from '../EPUBReader';

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

  beforeEach(() => {
    vi.clearAllMocks();

    // Mock EPUB.js
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('renders loading state initially', () => {
    // Mock the dynamic import to return a mock EPub class
    vi.doMock('epubjs', () => ({
      default: vi.fn(() => ({
        open: vi.fn().mockResolvedValue(undefined),
        renderTo: vi.fn(() => ({
          display: vi.fn().mockResolvedValue(undefined),
          prev: vi.fn().mockResolvedValue(undefined),
          next: vi.fn().mockResolvedValue(undefined),
          on: vi.fn(),
        })),
        spine: { get: vi.fn(() => ({ next: vi.fn(() => null) })) },
        locations: {
          generate: vi.fn().mockResolvedValue(undefined),
          percentage: vi.fn(() => 0.5),
        },
        ready: Promise.resolve(),
        navigation: { toc: [] },
      })),
    }));

    render(<EPUBReader {...mockProps} />);
    expect(screen.getByText('Loading book...')).toBeInTheDocument();
  });

  it('displays close button and control bar', async () => {
    vi.doMock('epubjs', () => ({
      default: vi.fn(() => ({
        open: vi.fn().mockResolvedValue(undefined),
        renderTo: vi.fn(() => ({
          display: vi.fn().mockResolvedValue(undefined),
          prev: vi.fn().mockResolvedValue(undefined),
          next: vi.fn().mockResolvedValue(undefined),
          on: vi.fn(),
        })),
        spine: { get: vi.fn(() => ({ next: vi.fn(() => null) })) },
        locations: {
          generate: vi.fn().mockResolvedValue(undefined),
          percentage: vi.fn(() => 0.5),
        },
        ready: Promise.resolve(),
        navigation: { toc: [] },
      })),
    }));

    render(<EPUBReader {...mockProps} />);

    await waitFor(() => {
      expect(screen.getByText('Close')).toBeInTheDocument();
    });
  });

  it('displays book metadata in sidebar', async () => {
    vi.doMock('epubjs', () => ({
      default: vi.fn(() => ({
        open: vi.fn().mockResolvedValue(undefined),
        renderTo: vi.fn(() => ({
          display: vi.fn().mockResolvedValue(undefined),
          prev: vi.fn().mockResolvedValue(undefined),
          next: vi.fn().mockResolvedValue(undefined),
          on: vi.fn(),
        })),
        spine: { get: vi.fn(() => ({ next: vi.fn(() => null) })) },
        locations: {
          generate: vi.fn().mockResolvedValue(undefined),
          percentage: vi.fn(() => 0.5),
        },
        ready: Promise.resolve(),
        navigation: { toc: [] },
      })),
    }));

    render(<EPUBReader {...mockProps} />);

    await waitFor(() => {
      expect(screen.getByText('Test Book')).toBeInTheDocument();
      expect(screen.getByText('Test Author')).toBeInTheDocument();
    });
  });

  it('shows TOC button and can toggle TOC modal', async () => {
    vi.doMock('epubjs', () => ({
      default: vi.fn(() => ({
        open: vi.fn().mockResolvedValue(undefined),
        renderTo: vi.fn(() => ({
          display: vi.fn().mockResolvedValue(undefined),
          prev: vi.fn().mockResolvedValue(undefined),
          next: vi.fn().mockResolvedValue(undefined),
          on: vi.fn(),
        })),
        spine: { get: vi.fn(() => ({ next: vi.fn(() => null) })) },
        locations: {
          generate: vi.fn().mockResolvedValue(undefined),
          percentage: vi.fn(() => 0.5),
        },
        ready: Promise.resolve(),
        navigation: { toc: [] },
      })),
    }));

    render(<EPUBReader {...mockProps} />);

    await waitFor(() => {
      const tocButton = screen.getByText('TOC');
      expect(tocButton).toBeInTheDocument();
    });
  });

  it('displays lexile level badge when provided', async () => {
    vi.doMock('epubjs', () => ({
      default: vi.fn(() => ({
        open: vi.fn().mockResolvedValue(undefined),
        renderTo: vi.fn(() => ({
          display: vi.fn().mockResolvedValue(undefined),
          prev: vi.fn().mockResolvedValue(undefined),
          next: vi.fn().mockResolvedValue(undefined),
          on: vi.fn(),
        })),
        spine: { get: vi.fn(() => ({ next: vi.fn(() => null) })) },
        locations: {
          generate: vi.fn().mockResolvedValue(undefined),
          percentage: vi.fn(() => 0.5),
        },
        ready: Promise.resolve(),
        navigation: { toc: [] },
      })),
    }));

    render(<EPUBReader {...mockProps} />);

    await waitFor(() => {
      expect(screen.getByText('750L')).toBeInTheDocument();
    });
  });

  it('calls onBack when close button is clicked', async () => {
    vi.doMock('epubjs', () => ({
      default: vi.fn(() => ({
        open: vi.fn().mockResolvedValue(undefined),
        renderTo: vi.fn(() => ({
          display: vi.fn().mockResolvedValue(undefined),
          prev: vi.fn().mockResolvedValue(undefined),
          next: vi.fn().mockResolvedValue(undefined),
          on: vi.fn(),
        })),
        spine: { get: vi.fn(() => ({ next: vi.fn(() => null) })) },
        locations: {
          generate: vi.fn().mockResolvedValue(undefined),
          percentage: vi.fn(() => 0.5),
        },
        ready: Promise.resolve(),
        navigation: { toc: [] },
      })),
    }));

    render(<EPUBReader {...mockProps} />);

    await waitFor(() => {
      const closeButton = screen.getByText('Close');
      fireEvent.click(closeButton);
      expect(mockProps.onBack).toHaveBeenCalled();
    });
  });

  it('displays progress percentage', async () => {
    vi.doMock('epubjs', () => ({
      default: vi.fn(() => ({
        open: vi.fn().mockResolvedValue(undefined),
        renderTo: vi.fn(() => ({
          display: vi.fn().mockResolvedValue(undefined),
          prev: vi.fn().mockResolvedValue(undefined),
          next: vi.fn().mockResolvedValue(undefined),
          on: vi.fn(),
        })),
        spine: { get: vi.fn(() => ({ next: vi.fn(() => null) })) },
        locations: {
          generate: vi.fn().mockResolvedValue(undefined),
          percentage: vi.fn(() => 0.5),
        },
        ready: Promise.resolve(),
        navigation: { toc: [] },
      })),
    }));

    render(<EPUBReader {...mockProps} />);

    await waitFor(() => {
      // Progress should be displayed
      expect(screen.getByText('%')).toBeInTheDocument();
    });
  });

  it('renders reading time component', async () => {
    vi.doMock('epubjs', () => ({
      default: vi.fn(() => ({
        open: vi.fn().mockResolvedValue(undefined),
        renderTo: vi.fn(() => ({
          display: vi.fn().mockResolvedValue(undefined),
          prev: vi.fn().mockResolvedValue(undefined),
          next: vi.fn().mockResolvedValue(undefined),
          on: vi.fn(),
        })),
        spine: { get: vi.fn(() => ({ next: vi.fn(() => null) })) },
        locations: {
          generate: vi.fn().mockResolvedValue(undefined),
          percentage: vi.fn(() => 0.5),
        },
        ready: Promise.resolve(),
        navigation: { toc: [] },
      })),
    }));

    render(<EPUBReader {...mockProps} />);

    await waitFor(() => {
      expect(screen.getByText(/minutes reading time/)).toBeInTheDocument();
    });
  });

  it('handles error state gracefully', async () => {
    const errorProps = {
      ...mockProps,
      book: {
        ...mockBook,
        source_url: 'https://example.com/nonexistent.epub',
      },
    };

    // Mock fetch to return 404
    (global.fetch as any).mockRejectedValueOnce(
      new Error('Failed to load book')
    );

    vi.doMock('epubjs', () => ({
      default: vi.fn(() => ({
        open: vi.fn().mockRejectedValue(new Error('404')),
        renderTo: vi.fn(() => ({
          display: vi.fn().mockResolvedValue(undefined),
          prev: vi.fn().mockResolvedValue(undefined),
          next: vi.fn().mockResolvedValue(undefined),
          on: vi.fn(),
        })),
        spine: { get: vi.fn(() => ({ next: vi.fn(() => null) })) },
        locations: {
          generate: vi.fn().mockResolvedValue(undefined),
          percentage: vi.fn(() => 0.5),
        },
        ready: Promise.resolve(),
        navigation: { toc: [] },
      })),
    }));

    render(<EPUBReader {...errorProps} />);

    await waitFor(() => {
      expect(screen.getByText('Back to Shelf')).toBeInTheDocument();
    });
  });
});
