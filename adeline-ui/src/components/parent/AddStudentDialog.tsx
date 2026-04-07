'use client';

import { useState } from 'react';
import { X, Loader2 } from 'lucide-react';

interface AddStudentDialogProps {
  onClose: () => void;
  onAdd: (name: string, email: string, gradeLevel: string) => Promise<void>;
}

export function AddStudentDialog({ onClose, onAdd }: AddStudentDialogProps) {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [gradeLevel, setGradeLevel] = useState('8');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      await onAdd(name, email, gradeLevel);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add student');
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-[#2F4731]" style={{ fontFamily: 'var(--font-emilys-candy), cursive' }}>
            Add Student
          </h2>
          <button
            onClick={onClose}
            className="text-[#2F4731]/60 hover:text-[#2F4731] transition-colors"
            disabled={loading}
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="name" className="block text-sm font-semibold text-[#2F4731] mb-2">
              Student Name *
            </label>
            <input
              id="name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Enter student's full name"
              className="w-full px-4 py-3 border-2 border-[#E7DAC3] rounded-lg focus:outline-none focus:border-[#BD6809] focus:ring-2 focus:ring-[#BD6809]/20"
              required
              disabled={loading}
            />
          </div>

          <div>
            <label htmlFor="email" className="block text-sm font-semibold text-[#2F4731] mb-2">
              Email Address *
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="student@example.com"
              className="w-full px-4 py-3 border-2 border-[#E7DAC3] rounded-lg focus:outline-none focus:border-[#BD6809] focus:ring-2 focus:ring-[#BD6809]/20"
              required
              disabled={loading}
            />
          </div>

          <div>
            <label htmlFor="gradeLevel" className="block text-sm font-semibold text-[#2F4731] mb-2">
              Grade Level *
            </label>
            <select
              id="gradeLevel"
              value={gradeLevel}
              onChange={(e) => setGradeLevel(e.target.value)}
              className="w-full px-4 py-3 border-2 border-[#E7DAC3] rounded-lg focus:outline-none focus:border-[#BD6809] focus:ring-2 focus:ring-[#BD6809]/20"
              disabled={loading}
            >
              {Array.from({ length: 13 }, (_, i) => i).map((grade) => (
                <option key={grade} value={grade.toString()}>
                  {grade === 0 ? 'Kindergarten' : `Grade ${grade}`}
                </option>
              ))}
            </select>
          </div>

          {error && (
            <div className="px-4 py-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}

          {/* Buttons */}
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="flex-1 px-4 py-3 bg-[#E7DAC3] text-[#2F4731] font-semibold rounded-lg hover:bg-[#2F4731] hover:text-white transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !name || !email}
              className="flex-1 px-4 py-3 bg-[#BD6809] text-white font-semibold rounded-lg hover:bg-[#2F4731] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              Add Student
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
