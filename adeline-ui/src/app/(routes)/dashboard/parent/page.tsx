'use client';

import { useState, useEffect, useCallback } from 'react';
import { Loader2, Users, BookOpen, Trophy, Plus, Settings, TrendingUp } from 'lucide-react';
import { getFamilyDashboard, listStudents, addStudent, type FamilyDashboard, type StudentSummary } from '@/lib/parent-client';
import { AddStudentDialog } from '@/components/parent/AddStudentDialog';
import { FamilyProgressGrid } from '@/components/parent/FamilyProgressGrid';
import { StudentSwitcher } from '@/components/parent/StudentSwitcher';

export default function ParentDashboardPage() {
  const [dashboard, setDashboard] = useState<FamilyDashboard | null>(null);
  const [students, setStudents] = useState<StudentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAddStudent, setShowAddStudent] = useState(false);
  const [selectedStudentId, setSelectedStudentId] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const [dashboardData, studentsData] = await Promise.all([
        getFamilyDashboard(),
        listStudents(),
      ]);
      setDashboard(dashboardData);
      setStudents(studentsData);
      
      // Auto-select first student if none selected
      if (!selectedStudentId && studentsData.length > 0) {
        setSelectedStudentId(studentsData[0].id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard');
      console.error('Error loading parent dashboard:', err);
    } finally {
      setLoading(false);
    }
  }, [selectedStudentId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleAddStudent = useCallback(async (name: string, email: string, gradeLevel: string) => {
    try {
      await addStudent({ name, email, grade_level: gradeLevel });
      setShowAddStudent(false);
      fetchData(); // Refresh data
    } catch (err) {
      throw err; // Let dialog handle error display
    }
  }, [fetchData]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-[#FFFEF7]">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-[#BD6809] mx-auto mb-4" />
          <p className="text-[#2F4731]/60">Loading family dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen bg-[#FFFEF7] px-4">
        <div className="text-center max-w-md">
          <p className="text-red-600 font-semibold mb-2">Error loading dashboard</p>
          <p className="text-sm text-red-500 mb-4">{error}</p>
          <button
            onClick={fetchData}
            className="px-4 py-2 bg-[#2F4731] text-white rounded-lg hover:bg-[#BD6809] transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#FFFEF7] pb-12">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="px-6 py-8 border-b border-[#E7DAC3]">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1
                className="text-4xl font-bold text-[#2F4731]"
                style={{ fontFamily: 'var(--font-emilys-candy), cursive' }}
              >
                Family Dashboard
              </h1>
              <p className="text-sm text-[#2F4731]/60 mt-2">
                Track progress across all your students
              </p>
            </div>
            <button
              onClick={() => setShowAddStudent(true)}
              className="flex items-center gap-2 px-4 py-2 bg-[#BD6809] text-white rounded-lg hover:bg-[#2F4731] transition-colors font-semibold"
            >
              <Plus className="w-4 h-4" />
              Add Student
            </button>
          </div>

          {/* Student Switcher */}
          {students.length > 0 && (
            <StudentSwitcher
              students={students}
              selectedStudentId={selectedStudentId}
              onSelectStudent={setSelectedStudentId}
            />
          )}
        </div>

        {/* Overview Cards */}
        {dashboard && (
          <div className="px-6 py-6">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
              <div className="rounded-2xl border-2 border-[#E7DAC3] bg-white p-6">
                <div className="flex items-center gap-3 mb-2">
                  <Users className="w-5 h-5 text-[#BD6809]" />
                  <p className="text-sm font-bold text-[#2F4731]/60">Total Students</p>
                </div>
                <p className="text-3xl font-bold text-[#2F4731]">{dashboard.total_students}</p>
              </div>

              <div className="rounded-2xl border-2 border-[#E7DAC3] bg-white p-6">
                <div className="flex items-center gap-3 mb-2">
                  <TrendingUp className="w-5 h-5 text-[#166534]" />
                  <p className="text-sm font-bold text-[#2F4731]/60">Family Credits</p>
                </div>
                <p className="text-3xl font-bold text-[#2F4731]">{dashboard.family_total_credits}</p>
              </div>

              <div className="rounded-2xl border-2 border-[#E7DAC3] bg-white p-6">
                <div className="flex items-center gap-3 mb-2">
                  <BookOpen className="w-5 h-5 text-[#9A3F4A]" />
                  <p className="text-sm font-bold text-[#2F4731]/60">Total Lessons</p>
                </div>
                <p className="text-3xl font-bold text-[#2F4731]">
                  {dashboard.students.reduce((sum, s) => sum + s.lessons_completed, 0)}
                </p>
              </div>

              <div className="rounded-2xl border-2 border-[#E7DAC3] bg-white p-6">
                <div className="flex items-center gap-3 mb-2">
                  <Trophy className="w-5 h-5 text-[#BD6809]" />
                  <p className="text-sm font-bold text-[#2F4731]/60">Total Projects</p>
                </div>
                <p className="text-3xl font-bold text-[#2F4731]">
                  {dashboard.students.reduce((sum, s) => sum + s.projects_sealed, 0)}
                </p>
              </div>
            </div>

            {/* Progress Grid */}
            <FamilyProgressGrid students={dashboard.students} />

            {/* Recent Activity */}
            <div className="mt-8">
              <h2 className="text-2xl font-bold text-[#2F4731] mb-4" style={{ fontFamily: 'var(--font-emilys-candy), cursive' }}>
                Recent Activity
              </h2>
              <div className="rounded-2xl border-2 border-[#E7DAC3] bg-white overflow-hidden">
                {dashboard.recent_activity.length === 0 ? (
                  <div className="p-8 text-center">
                    <p className="text-[#2F4731]/60">No recent activity yet</p>
                  </div>
                ) : (
                  <div className="divide-y divide-[#E7DAC3]">
                    {dashboard.recent_activity.map((activity, idx) => (
                      <div key={idx} className="p-4 hover:bg-[#FFFEF7] transition-colors">
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="font-semibold text-[#2F4731]">{activity.student_name}</p>
                            <p className="text-sm text-[#2F4731]/60">
                              Completed lesson in {activity.track.replace(/_/g, ' ')}
                            </p>
                          </div>
                          <p className="text-xs text-[#2F4731]/40">
                            {activity.completed_at
                              ? new Date(activity.completed_at).toLocaleDateString()
                              : 'Recently'}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Add Student Dialog */}
      {showAddStudent && (
        <AddStudentDialog
          onClose={() => setShowAddStudent(false)}
          onAdd={handleAddStudent}
        />
      )}
    </div>
  );
}
