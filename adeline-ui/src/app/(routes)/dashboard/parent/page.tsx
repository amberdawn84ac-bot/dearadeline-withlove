'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { Loader2, Users, BookOpen, Trophy, Plus, TrendingUp, GraduationCap, ExternalLink, LibraryBig, CheckCircle2, CircleDashed } from 'lucide-react';
import { getFamilyDashboard, listStudents, addStudent, type FamilyDashboard, type StudentSummary } from '@/lib/parent-client';
import { getLearningPlan, type LearningPlanResponse } from '@/lib/brain-client';
import { AddStudentDialog } from '@/components/parent/AddStudentDialog';
import { ClaimStudentDialog } from '@/components/parent/ClaimStudentDialog';
import { FamilyProgressGrid } from '@/components/parent/FamilyProgressGrid';
import { StudentSwitcher } from '@/components/parent/StudentSwitcher';

export default function ParentDashboardPage() {
  const [dashboard, setDashboard] = useState<FamilyDashboard | null>(null);
  const [students, setStudents] = useState<StudentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAddStudent, setShowAddStudent] = useState(false);
  const [showClaimStudent, setShowClaimStudent] = useState(false);
  const [selectedStudentId, setSelectedStudentId] = useState<string | null>(null);
  const [studentPlan, setStudentPlan] = useState<LearningPlanResponse | null>(null);
  const [planLoading, setPlanLoading] = useState(false);

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

  // Fetch selected student's learning plan
  useEffect(() => {
    if (!selectedStudentId) {
      setStudentPlan(null);
      return;
    }
    setPlanLoading(true);
    getLearningPlan(selectedStudentId, 4)
      .then(setStudentPlan)
      .catch(() => setStudentPlan(null))
      .finally(() => setPlanLoading(false));
  }, [selectedStudentId]);

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
            <div className="flex items-center gap-3">
              <button
                onClick={() => setShowClaimStudent(true)}
                className="px-4 py-2 bg-white border border-[#2F4731]/20 hover:border-[#BD6809] text-[#2F4731] rounded-lg font-semibold text-sm"
              >
                Link a Mobile Kid
              </button>
              <button
                onClick={() => setShowAddStudent(true)}
                className="flex items-center gap-2 px-4 py-2 bg-[#BD6809] text-white rounded-lg hover:bg-[#2F4731] transition-colors font-semibold"
              >
                <Plus className="w-4 h-4" />
                Add Student
              </button>
            </div>
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

            {/* Parent-only source curation */}
            <section className="mt-8 rounded-2xl border-2 border-[#E7DAC3] bg-white p-5 sm:p-6">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-start gap-3">
                  <div className="rounded-xl bg-[#2F4731]/10 p-2.5">
                    <LibraryBig className="h-5 w-5 text-[#2F4731]" />
                  </div>
                  <div>
                    <h2 className="font-bold text-[#2F4731]">Adeline&rsquo;s Source Room</h2>
                    <p className="mt-1 max-w-2xl text-sm leading-relaxed text-[#2F4731]/60">
                      Review the primary sources, simulations, games, and open curriculum Adeline can draw from. Students receive the relevant source inside their learning plan or lesson instead of browsing the full catalog.
                    </p>
                  </div>
                </div>
                <Link
                  href="/dashboard/parent/resources"
                  className="inline-flex shrink-0 items-center justify-center gap-2 rounded-lg bg-[#2F4731] px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[#BD6809]"
                >
                  Review sources <ExternalLink className="h-4 w-4" />
                </Link>
              </div>
            </section>

            {/* Selected Student Detail */}
            {selectedStudentId && (
              <div className="mt-8">
                <h2 className="text-2xl font-bold text-[#2F4731] mb-4" style={{ fontFamily: 'var(--font-emilys-candy), cursive' }}>
                  {students.find(s => s.id === selectedStudentId)?.name || 'Student'}&rsquo;s Plan
                </h2>

                {planLoading && (
                  <div className="flex items-center gap-3 py-8 justify-center">
                    <Loader2 className="w-5 h-5 animate-spin text-[#BD6809]" />
                    <p className="text-sm text-[#2F4731]/60">Loading learning plan...</p>
                  </div>
                )}

                {!planLoading && studentPlan && (
                  <div className="space-y-6">
                    {/* Credits + Progress */}
                    <div className="flex flex-wrap items-center gap-6 p-4 bg-white rounded-xl border border-[#E7DAC3]">
                      <div className="flex items-center gap-2">
                        <GraduationCap className="w-5 h-5 text-[#BD6809]" />
                        <div>
                          <p className="text-xs text-[#2F4731]/60">Credits Earned</p>
                          <p className="text-lg font-bold text-[#2F4731]">{studentPlan.total_credits_earned.toFixed(1)}</p>
                        </div>
                      </div>
                      {studentPlan.strongest_track && (
                        <>
                          <div className="h-8 w-px bg-[#E7DAC3]" />
                          <div>
                            <p className="text-xs text-[#2F4731]/60">Strongest</p>
                            <p className="text-sm font-bold text-[#166534]">{studentPlan.strongest_track.replace(/_/g, ' ')}</p>
                          </div>
                        </>
                      )}
                      {studentPlan.weakest_track && (
                        <>
                          <div className="h-8 w-px bg-[#E7DAC3]" />
                          <div>
                            <p className="text-xs text-[#2F4731]/60">Needs Focus</p>
                            <p className="text-sm font-bold text-[#BD6809]">{studentPlan.weakest_track.replace(/_/g, ' ')}</p>
                          </div>
                        </>
                      )}
                      <Link
                        href="/dashboard/transcript"
                        className="ml-auto inline-flex items-center gap-2 rounded-lg bg-[#2F4731] px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-[#BD6809]"
                      >
                        Transcript &amp; graduation <ExternalLink className="h-4 w-4" />
                      </Link>
                    </div>

                    {/* Parent-only concept map. Children see experiences, not standards. */}
                    <section className="rounded-2xl border-2 border-[#E7DAC3] bg-white p-5 sm:p-6">
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
                        <div>
                          <p className="text-xs font-black uppercase tracking-[.16em] text-[#BD6809]">Parent learning map</p>
                          <h3 className="mt-1 text-2xl font-bold text-[#2F4731]" style={{ fontFamily: 'var(--font-emilys-candy), cursive' }}>
                            What has been learned - and what remains
                          </h3>
                          <p className="mt-2 max-w-3xl text-sm leading-6 text-[#2F4731]/65">
                            Adeline uses this private checklist to choose experiences, games, books, projects, and review. The child never has to march through this list.
                          </p>
                        </div>
                        <div className="shrink-0 text-left sm:text-right">
                          <p className="text-3xl font-black text-[#2F4731]">
                            {studentPlan.coverage.mastered}<span className="text-lg text-[#2F4731]/40"> / {studentPlan.coverage.total_required}</span>
                          </p>
                          <p className="text-xs font-bold text-[#2F4731]/55">concepts demonstrated</p>
                        </div>
                      </div>
                      <div className="mt-5 h-3 overflow-hidden rounded-full bg-[#E7DAC3]">
                        <div className="h-full rounded-full bg-[#4F7A58] transition-all" style={{ width: `${studentPlan.coverage.total_required ? Math.round((studentPlan.coverage.mastered / studentPlan.coverage.total_required) * 100) : 0}%` }} />
                      </div>
                      {studentPlan.grade_standards.length ? (
                        <div className="mt-6 space-y-3">
                          {Array.from(new Set(studentPlan.grade_standards.map((standard) => standard.subject))).sort().map((subject) => {
                            const concepts = studentPlan.grade_standards.filter((standard) => standard.subject === subject);
                            const mastered = concepts.filter((standard) => standard.mastered).length;
                            return <details key={subject} className="group rounded-xl border border-[#E7DAC3] bg-[#FFFEF9] open:bg-white">
                              <summary className="flex cursor-pointer list-none items-center gap-3 p-4">
                                <span className="flex h-9 w-9 items-center justify-center rounded-full bg-[#2F4731]/10 text-sm font-black text-[#2F4731]">{mastered}/{concepts.length}</span>
                                <div className="min-w-0 flex-1"><p className="font-bold text-[#2F4731]">{subject}</p><p className="text-xs text-[#2F4731]/55">{concepts.length - mastered} still to demonstrate</p></div>
                                <span className="text-sm font-bold text-[#BD6809] group-open:hidden">See concepts</span><span className="hidden text-sm font-bold text-[#BD6809] group-open:inline">Hide</span>
                              </summary>
                              <div className="border-t border-[#E7DAC3] px-4 py-2">
                                {concepts.map((concept) => <div key={concept.standard_id} className="flex gap-3 border-b border-[#E7DAC3]/70 py-3 last:border-0">
                                  {concept.mastered ? <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-[#4F7A58]" aria-label="Demonstrated" /> : <CircleDashed className="mt-0.5 h-5 w-5 shrink-0 text-[#BD6809]" aria-label="Still learning" />}
                                  <div><p className={`text-sm leading-5 ${concept.mastered ? 'text-[#2F4731]/60' : 'font-semibold text-[#2F4731]'}`}>{concept.description}</p><p className="mt-1 text-[11px] font-bold uppercase tracking-wide text-[#2F4731]/40">{{ NOT_STARTED: 'Not started', DEVELOPING: 'Introduced · more experience needed', APPROACHING: 'Practicing · not yet demonstrated', UNDERSTANDING: 'Demonstrated with evidence', EXTENDING: 'Demonstrated and applied deeply' }[concept.proficiency]}</p></div>
                                </div>)}
                              </div>
                            </details>;
                          })}
                        </div>
                      ) : <p className="mt-5 rounded-xl bg-[#FFF8EC] p-4 text-sm text-[#2F4731]/65">Adeline has not loaded this student&rsquo;s grade-level concept records yet. Placement evidence will establish the working grade before the checklist is used.</p>}
                    </section>

                    {/* Recommended Lessons */}
                    {studentPlan.suggestions.length > 0 && (
                      <div>
                        <p className="text-sm font-bold text-[#2F4731] mb-3">Recommended Lessons</p>
                        <div className="grid sm:grid-cols-2 gap-3">
                          {studentPlan.suggestions.slice(0, 4).map(s => (
                            <div key={s.id} className="p-3 rounded-xl border border-[#E7DAC3] bg-white">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="text-xl">{s.emoji}</span>
                                <h4 className="text-sm font-bold text-[#2F4731]">{s.title}</h4>
                              </div>
                              <p className="text-xs text-[#2F4731]/60 line-clamp-2">{s.description}</p>
                              <span className="inline-block mt-2 px-2 py-0.5 text-[10px] font-bold rounded-full bg-[#2F4731]/10 text-[#2F4731]">
                                {s.track.replace(/_/g, ' ')}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Recommended Books */}
                    {studentPlan.recommended_books && studentPlan.recommended_books.length > 0 && (
                      <div>
                        <p className="text-sm font-bold text-[#2F4731] mb-3">Recommended Reading</p>
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                          {studentPlan.recommended_books.map(book => (
                            <div key={book.id} className="p-3 rounded-xl border border-[#E7DAC3] bg-white">
                              <div className="w-full aspect-[2/3] rounded-lg mb-2 overflow-hidden bg-[#F5F0E8] flex items-center justify-center">
                                {book.cover_url ? (
                                  <img src={book.cover_url} alt={book.title} className="w-full h-full object-cover" />
                                ) : (
                                  <BookOpen className="w-6 h-6 text-[#2F4731]/20" />
                                )}
                              </div>
                              <h4 className="text-xs font-bold text-[#2F4731] line-clamp-2">{book.title}</h4>
                              <p className="text-[10px] text-[#2F4731]/50 mt-0.5">{book.author}</p>
                              <div className="flex gap-1 mt-1">
                                <span className="px-1.5 py-0.5 text-[9px] font-bold rounded-full bg-[#2F4731]/10 text-[#2F4731]">
                                  {book.track.replace(/_/g, ' ')}
                                </span>
                                <span className="px-1.5 py-0.5 text-[9px] rounded-full border border-[#E7DAC3] text-[#2F4731]/50">
                                  {book.lexile_level}L
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {!planLoading && !studentPlan && (
                  <div className="p-6 text-center bg-white rounded-xl border border-[#E7DAC3]">
                    <p className="text-sm text-[#2F4731]/60">Select a student above to see their learning plan and recommendations.</p>
                  </div>
                )}
              </div>
            )}

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

      {showClaimStudent && (
        <ClaimStudentDialog
          onClose={() => setShowClaimStudent(false)}
          onClaimed={fetchData}
        />
      )}
    </div>
  );
}
