'use client';

import { createContext, useContext, useEffect, useState, ReactNode } from 'react';

interface StudentProfile {
  id: string;
  name: string;
  gradeLevel: string;
  interests: string[];
  learningStyle: string | null;
  state: string | null;
  onboardingComplete: boolean;
}

interface StudentContextValue {
  student: StudentProfile | null;
  loading: boolean;
  refresh: () => Promise<void>;
}

const StudentContext = createContext<StudentContextValue>({
  student: null,
  loading: true,
  refresh: async () => undefined,
});

export function StudentProvider({ children }: { children: ReactNode }) {
  const [student, setStudent] = useState<StudentProfile | null>(null);
  const [loading, setLoading] = useState(true);

  async function loadStudent() {
    setLoading(true);
    try {
      const response = await fetch('/api/student-auth', {
        method: 'GET',
        cache: 'no-store',
        credentials: 'same-origin',
      });
      if (!response.ok) {
        setStudent(null);
        return;
      }
      const data = await response.json();
      if (!data?.user || !data?.student_id) {
        setStudent(null);
        return;
      }
      setStudent({
        id: data.student_id,
        name: data.user.name ?? data.user.display_name ?? 'Student',
        gradeLevel: data.user.gradeLevel ?? data.user.grade_level ?? '8',
        interests: data.user.interests ?? [],
        learningStyle: data.user.learningStyle ?? null,
        state: data.user.state ?? null,
        onboardingComplete: data.user.onboardingComplete ?? true,
      });
    } catch (error) {
      console.error('[StudentProvider] Failed to load secure student session:', error);
      setStudent(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadStudent();
  }, []);

  return (
    <StudentContext.Provider value={{ student, loading, refresh: loadStudent }}>
      {children}
    </StudentContext.Provider>
  );
}

export function useStudent() {
  return useContext(StudentContext);
}
