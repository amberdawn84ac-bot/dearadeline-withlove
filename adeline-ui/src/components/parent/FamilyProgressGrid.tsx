'use client';

import { BookOpen, Trophy, Book, TrendingUp } from 'lucide-react';
import type { StudentProgress } from '@/lib/parent-client';

interface FamilyProgressGridProps {
  students: StudentProgress[];
}

const TRACK_COLORS: Record<string, string> = {
  CREATION_SCIENCE: '#166534',
  HEALTH_NATUROPATHY: '#9A3F4A',
  HOMESTEADING: '#166534',
  GOVERNMENT_ECONOMICS: '#BD6809',
  JUSTICE_CHANGEMAKING: '#9A3F4A',
  DISCIPLESHIP: '#2F4731',
  TRUTH_HISTORY: '#9A3F4A',
  ENGLISH_LITERATURE: '#BD6809',
  APPLIED_MATHEMATICS: '#166534',
  CREATIVE_ECONOMY: '#BD6809',
};

export function FamilyProgressGrid({ students }: FamilyProgressGridProps) {
  if (students.length === 0) {
    return (
      <div className="rounded-2xl border-2 border-[#E7DAC3] bg-white p-8 text-center">
        <p className="text-[#2F4731]/60">No students added yet. Click "Add Student" to get started.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {students.map((student) => (
        <div
          key={student.student_id}
          className="rounded-2xl border-2 border-[#E7DAC3] bg-white p-6 hover:shadow-lg transition-shadow"
        >
          {/* Student Name */}
          <div className="mb-4">
            <h3 className="text-xl font-bold text-[#2F4731]" style={{ fontFamily: 'var(--font-emilys-candy), cursive' }}>
              {student.student_name}
            </h3>
            {student.active_track && (
              <span
                className="inline-block mt-2 px-2 py-1 text-xs font-bold rounded-full text-white"
                style={{ backgroundColor: TRACK_COLORS[student.active_track] || '#2F4731' }}
              >
                {student.active_track.replace(/_/g, ' ')}
              </span>
            )}
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-lg bg-[#FFFEF7] p-3">
              <div className="flex items-center gap-2 mb-1">
                <TrendingUp className="w-4 h-4 text-[#166534]" />
                <p className="text-xs font-bold text-[#2F4731]/60">Credits</p>
              </div>
              <p className="text-2xl font-bold text-[#2F4731]">{student.total_credits}</p>
            </div>

            <div className="rounded-lg bg-[#FFFEF7] p-3">
              <div className="flex items-center gap-2 mb-1">
                <BookOpen className="w-4 h-4 text-[#9A3F4A]" />
                <p className="text-xs font-bold text-[#2F4731]/60">Lessons</p>
              </div>
              <p className="text-2xl font-bold text-[#2F4731]">{student.lessons_completed}</p>
            </div>

            <div className="rounded-lg bg-[#FFFEF7] p-3">
              <div className="flex items-center gap-2 mb-1">
                <Book className="w-4 h-4 text-[#BD6809]" />
                <p className="text-xs font-bold text-[#2F4731]/60">Books</p>
              </div>
              <p className="text-2xl font-bold text-[#2F4731]">{student.books_finished}</p>
            </div>

            <div className="rounded-lg bg-[#FFFEF7] p-3">
              <div className="flex items-center gap-2 mb-1">
                <Trophy className="w-4 h-4 text-[#BD6809]" />
                <p className="text-xs font-bold text-[#2F4731]/60">Projects</p>
              </div>
              <p className="text-2xl font-bold text-[#2F4731]">{student.projects_sealed}</p>
            </div>
          </div>

          {/* Last Activity */}
          {student.last_activity && (
            <div className="mt-4 pt-4 border-t border-[#E7DAC3]">
              <p className="text-xs text-[#2F4731]/60">
                Last active: {new Date(student.last_activity).toLocaleDateString()}
              </p>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
