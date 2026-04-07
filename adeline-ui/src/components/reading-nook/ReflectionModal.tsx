'use client';

import { useState, useCallback } from 'react';
import { Loader2, X } from 'lucide-react';

interface ReflectionModalProps {
  sessionId: string;
  studentId: string;
  bookTitle: string;
  onClose: () => void;
  onSuccess: () => void;
}

export function ReflectionModal({
  sessionId,
  studentId,
  bookTitle,
  onClose,
  onSuccess,
}: ReflectionModalProps) {
  const [reflection, setReflection] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch(`/api/reading-session/${sessionId}`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${typeof window !== 'undefined' ? localStorage.getItem('auth_token') || '' : ''}`,
          },
          body: JSON.stringify({
            status: 'finished',
            student_reflection: reflection.trim() || null,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));

          if (response.status === 401) {
            setError('Session expired. Please log in again.');
          } else if (response.status === 404) {
            setError('Reading session not found.');
          } else if (response.status === 500) {
            setError('Server error. Please try again later.');
          } else {
            setError(errorData.message || 'Failed to save reflection.');
          }
          setIsLoading(false);
          return;
        }

        // Success
        onSuccess();
        onClose();
      } catch (err) {
        console.error('Error saving reflection:', err);
        setError('Network error. Please check your connection and try again.');
        setIsLoading(false);
      }
    },
    [sessionId, studentId, reflection, onClose, onSuccess]
  );

  const handleSkip = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/reading-session/${sessionId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${typeof window !== 'undefined' ? localStorage.getItem('auth_token') || '' : ''}`,
        },
        body: JSON.stringify({
          status: 'finished',
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        setError(errorData.message || 'Failed to mark book as complete.');
        setIsLoading(false);
        return;
      }

      // Success
      onSuccess();
      onClose();
    } catch (err) {
      console.error('Error marking book as complete:', err);
      setError('Network error. Please check your connection and try again.');
      setIsLoading(false);
    }
  }, [sessionId, studentId, onClose, onSuccess]);

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-lg w-full space-y-6 p-6">
        {/* ── Header ── */}
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-2xl font-bold text-[#2F4731]">You did it! 🎉</h2>
            <p className="text-sm text-[#2F4731]/60 mt-1">
              You finished <span className="font-semibold">{bookTitle}</span>
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-[#2F4731]/60 hover:text-[#2F4731] transition-colors"
            aria-label="Close modal"
            disabled={isLoading}
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* ── Form ── */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Text input */}
          <div>
            <label htmlFor="reflection" className="block text-sm font-semibold text-[#2F4731] mb-2">
              What was your favorite part? (Optional)
            </label>
            <textarea
              id="reflection"
              value={reflection}
              onChange={(e) => setReflection(e.target.value)}
              placeholder="Share your thoughts about this book..."
              className="w-full px-4 py-3 border-2 border-[#E7DAC3] rounded-lg focus:outline-none focus:border-[#BD6809] focus:ring-2 focus:ring-[#BD6809]/20 resize-none"
              rows={5}
              disabled={isLoading}
            />
          </div>

          {/* Character count */}
          <p className="text-xs text-[#2F4731]/60">{reflection.length} / 500 characters</p>

          {/* Error message */}
          {error && (
            <div className="px-4 py-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          {/* Buttons */}
          <div className="flex gap-3 pt-2">
            <button
              type="submit"
              disabled={isLoading}
              className="flex-1 px-4 py-3 bg-[#BD6809] text-white font-semibold rounded-lg hover:bg-[#2F4731] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
              Save & Close
            </button>
            <button
              type="button"
              onClick={handleSkip}
              disabled={isLoading}
              className="flex-1 px-4 py-3 bg-[#E7DAC3] text-[#2F4731] font-semibold rounded-lg hover:bg-[#2F4731] hover:text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isLoading && <Loader2 className="w-4 h-4 animate-spin" />}
              Skip
            </button>
          </div>
        </form>

        {/* ── Encouragement ── */}
        <div className="p-4 bg-[#FFFEF7] rounded-lg border border-[#E7DAC3]">
          <p className="text-sm text-[#2F4731]">
            <span className="font-semibold">Great work!</span> Your reading progress has been saved, and this book now appears in your "Finished" shelf. Keep reading!
          </p>
        </div>
      </div>
    </div>
  );
}
