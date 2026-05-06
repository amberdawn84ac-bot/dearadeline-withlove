'use client';

import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { useAuth } from './useAuth';

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
}

const StudentContext = createContext<StudentContextValue>({
  student: null,
  loading: true,
});

export function StudentProvider({ children }: { children: ReactNode }) {
  const { user, loading: authLoading } = useAuth();
  const [student, setStudent] = useState<StudentProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (authLoading) return;
    if (!user) {
      setStudent(null);
      setLoading(false);
      return;
    }

    const token = localStorage.getItem('auth_token');
    if (!token) {
      setLoading(false);
      return;
    }

    // Add cache-busting to prevent stale reads after onboarding completion
    const cacheBuster = Date.now();
    fetch(`/brain/api/onboarding?_=${cacheBuster}`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
      },
    })
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data?.user) {
          setStudent({
            id: user.id,
            name: data.user.name ?? '',
            gradeLevel: data.user.gradeLevel ?? '8',
            interests: data.user.interests ?? [],
            learningStyle: data.user.learningStyle ?? null,
            state: data.user.state ?? null,
            onboardingComplete: data.user.onboardingComplete ?? false,
          });
        }
      })
      .catch(err => console.error('[StudentProvider] Failed to fetch profile:', err))
      .finally(() => setLoading(false));
  }, [user, authLoading]);

  return (
    <StudentContext.Provider value={{ student, loading }}>
      {children}
    </StudentContext.Provider>
  );
}

export function useStudent() {
  return useContext(StudentContext);
}
