'use client';

import { ChevronDown } from 'lucide-react';
import { useState, useRef, useEffect } from 'react';
import type { StudentSummary } from '@/lib/parent-client';

interface StudentSwitcherProps {
  students: StudentSummary[];
  selectedStudentId: string | null;
  onSelectStudent: (studentId: string) => void;
}

export function StudentSwitcher({ students, selectedStudentId, onSelectStudent }: StudentSwitcherProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const selectedStudent = students.find(s => s.id === selectedStudentId);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen]);

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-3 px-4 py-3 rounded-xl border-2 border-[#E7DAC3] bg-white hover:border-[#BD6809] transition-colors min-w-[250px]"
      >
        <div className="flex-1 text-left">
          <p className="text-sm font-bold text-[#2F4731]">
            {selectedStudent ? selectedStudent.name : 'Select Student'}
          </p>
          {selectedStudent && (
            <p className="text-xs text-[#2F4731]/60">Grade {selectedStudent.grade_level}</p>
          )}
        </div>
        <ChevronDown className={`w-4 h-4 text-[#2F4731] transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 right-0 mt-2 bg-white rounded-xl border-2 border-[#E7DAC3] shadow-lg z-50 overflow-hidden">
          <div className="max-h-64 overflow-y-auto">
            {students.map((student) => (
              <button
                key={student.id}
                onClick={() => {
                  onSelectStudent(student.id);
                  setIsOpen(false);
                }}
                className={`w-full px-4 py-3 text-left hover:bg-[#FFFEF7] transition-colors border-b border-[#E7DAC3] last:border-b-0 ${
                  student.id === selectedStudentId ? 'bg-[#FDF6E9]' : ''
                }`}
              >
                <p className="text-sm font-semibold text-[#2F4731]">{student.name}</p>
                <p className="text-xs text-[#2F4731]/60">
                  Grade {student.grade_level} • {student.interests.length} interests
                </p>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
