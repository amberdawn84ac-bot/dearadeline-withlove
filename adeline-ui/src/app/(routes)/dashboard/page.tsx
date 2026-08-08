'use client';

import { Loader2 } from 'lucide-react';
import ConciergeDashboard from '@/components/ConciergeDashboard';
import { useStudent } from '@/lib/useStudent';

export default function DashboardPage() {
  const { student, loading } = useStudent();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#f5f0e5] text-[#244a35]">
        <Loader2 className="h-5 w-5 animate-spin" />
      </div>
    );
  }

  if (!student) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#f5f0e5] px-6 text-center text-[#244a35]">
        <div>
          <p className="font-serif text-2xl">Adeline is waiting.</p>
          <p className="mt-2 text-sm text-[#776b59]">Sign in to continue your conversation.</p>
        </div>
      </div>
    );
  }

  return (
    <ConciergeDashboard
      studentId={student.id}
      studentName={student.name}
      gradeLevel={student.gradeLevel}
    />
  );
}
