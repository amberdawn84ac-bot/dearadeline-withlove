import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ReflectionModal } from '../ReflectionModal';

describe('ReflectionModal', () => {
  const mockProps = {
    sessionId: 'session-123',
    studentId: 'student-123',
    bookTitle: 'The Great Gatsby',
    onClose: vi.fn(),
    onSuccess: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
  });

  it('renders completion message with book title', () => {
    render(<ReflectionModal {...mockProps} />);
    expect(screen.getByText('You did it! 🎉')).toBeInTheDocument();
    expect(screen.getByText(/The Great Gatsby/)).toBeInTheDocument();
  });

  it('has optional reflection textarea', () => {
    render(<ReflectionModal {...mockProps} />);
    const textarea = screen.getByPlaceholderText('Share your thoughts about this book...');
    expect(textarea).toBeInTheDocument();
    expect(textarea).not.toBeRequired();
  });

  it('updates character count as user types', () => {
    render(<ReflectionModal {...mockProps} />);
    const textarea = screen.getByPlaceholderText('Share your thoughts about this book...') as HTMLTextAreaElement;

    fireEvent.change(textarea, { target: { value: 'This was amazing!' } });
    expect(screen.getByText(/17 \/ 500 characters/)).toBeInTheDocument();
  });

  it('submits reflection with status=finished', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({}),
    });
    global.fetch = mockFetch;

    render(<ReflectionModal {...mockProps} />);
    const textarea = screen.getByPlaceholderText('Share your thoughts about this book...') as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: 'Amazing book!' } });

    fireEvent.click(screen.getByText('Save & Close'));

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/reading-session/session-123',
        expect.objectContaining({
          method: 'PATCH',
          body: JSON.stringify({
            status: 'finished',
            student_reflection: 'Amazing book!',
          }),
        })
      );
    });

    await waitFor(() => {
      expect(mockProps.onSuccess).toHaveBeenCalled();
      expect(mockProps.onClose).toHaveBeenCalled();
    });
  });

  it('submits empty reflection as null', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({}),
    });
    global.fetch = mockFetch;

    render(<ReflectionModal {...mockProps} />);
    fireEvent.click(screen.getByText('Save & Close'));

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/reading-session/session-123',
        expect.objectContaining({
          body: JSON.stringify({
            status: 'finished',
            student_reflection: null,
          }),
        })
      );
    });
  });

  it('handles skip button without reflection', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({}),
    });
    global.fetch = mockFetch;

    render(<ReflectionModal {...mockProps} />);
    fireEvent.click(screen.getByText('Skip'));

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/reading-session/session-123',
        expect.objectContaining({
          body: JSON.stringify({ status: 'finished' }),
        })
      );
    });

    await waitFor(() => {
      expect(mockProps.onSuccess).toHaveBeenCalled();
      expect(mockProps.onClose).toHaveBeenCalled();
    });
  });

  it('displays error on failed submission', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      json: vi.fn().mockResolvedValue({ message: 'Server error' }),
    });
    global.fetch = mockFetch;

    render(<ReflectionModal {...mockProps} />);
    fireEvent.click(screen.getByText('Save & Close'));

    await waitFor(() => {
      expect(screen.getByText('Server error. Please try again later.')).toBeInTheDocument();
    });

    expect(mockProps.onSuccess).not.toHaveBeenCalled();
    expect(mockProps.onClose).not.toHaveBeenCalled();
  });

  it('disables buttons during submission', async () => {
    let resolveF: any;
    const mockFetch = vi.fn(
      () =>
        new Promise((resolve: any) => {
          resolveF = resolve;
        })
    ) as any;
    global.fetch = mockFetch;

    render(<ReflectionModal {...mockProps} />);
    const submitButton = screen.getByText('Save & Close') as HTMLButtonElement;

    fireEvent.click(submitButton);

    expect(submitButton).toBeDisabled();
    expect((screen.getByText('Skip') as HTMLButtonElement).disabled).toBe(true);

    resolveF({ ok: true, json: vi.fn().mockResolvedValue({}) });

    await waitFor(() => {
      expect(mockProps.onSuccess).toHaveBeenCalled();
    });
  });

  it('closes modal when X button clicked', () => {
    render(<ReflectionModal {...mockProps} />);
    const closeButton = screen.getByLabelText('Close modal');

    fireEvent.click(closeButton);

    expect(mockProps.onClose).toHaveBeenCalled();
  });

  it('handles network error gracefully', async () => {
    const mockFetch = vi.fn().mockRejectedValue(new Error('Network error'));
    global.fetch = mockFetch;

    render(<ReflectionModal {...mockProps} />);
    fireEvent.click(screen.getByText('Save & Close'));

    await waitFor(() => {
      expect(screen.getByText('Network error. Please check your connection and try again.')).toBeInTheDocument();
    });

    expect(mockProps.onSuccess).not.toHaveBeenCalled();
  });

  it('handles 401 unauthorized error', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: vi.fn().mockResolvedValue({}),
    });
    global.fetch = mockFetch;

    render(<ReflectionModal {...mockProps} />);
    fireEvent.click(screen.getByText('Save & Close'));

    await waitFor(() => {
      expect(screen.getByText('Session expired. Please log in again.')).toBeInTheDocument();
    });
  });

  it('handles 404 not found error', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: vi.fn().mockResolvedValue({}),
    });
    global.fetch = mockFetch;

    render(<ReflectionModal {...mockProps} />);
    fireEvent.click(screen.getByText('Save & Close'));

    await waitFor(() => {
      expect(screen.getByText('Reading session not found.')).toBeInTheDocument();
    });
  });

  it('trims whitespace from reflection text', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: vi.fn().mockResolvedValue({}),
    });
    global.fetch = mockFetch;

    render(<ReflectionModal {...mockProps} />);
    const textarea = screen.getByPlaceholderText('Share your thoughts about this book...') as HTMLTextAreaElement;
    fireEvent.change(textarea, { target: { value: '   Amazing book!   ' } });

    fireEvent.click(screen.getByText('Save & Close'));

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/reading-session/session-123',
        expect.objectContaining({
          body: JSON.stringify({
            status: 'finished',
            student_reflection: 'Amazing book!',
          }),
        })
      );
    });
  });

  it('disables textarea during submission', async () => {
    let resolveF: any;
    const mockFetch = vi.fn(
      () =>
        new Promise((resolve: any) => {
          resolveF = resolve;
        })
    ) as any;
    global.fetch = mockFetch;

    render(<ReflectionModal {...mockProps} />);
    const textarea = screen.getByPlaceholderText('Share your thoughts about this book...') as HTMLTextAreaElement;
    const submitButton = screen.getByText('Save & Close');

    fireEvent.click(submitButton);

    expect(textarea.disabled).toBe(true);

    resolveF({ ok: true, json: vi.fn().mockResolvedValue({}) });

    await waitFor(() => {
      expect(mockProps.onSuccess).toHaveBeenCalled();
    });
  });

  it('disables X button during submission', async () => {
    let resolveF: any;
    const mockFetch = vi.fn(
      () =>
        new Promise((resolve: any) => {
          resolveF = resolve;
        })
    ) as any;
    global.fetch = mockFetch;

    render(<ReflectionModal {...mockProps} />);
    const closeButton = screen.getByLabelText('Close modal') as HTMLButtonElement;
    const submitButton = screen.getByText('Save & Close');

    fireEvent.click(submitButton);

    expect(closeButton.disabled).toBe(true);

    resolveF({ ok: true, json: vi.fn().mockResolvedValue({}) });

    await waitFor(() => {
      expect(mockProps.onSuccess).toHaveBeenCalled();
    });
  });
});
