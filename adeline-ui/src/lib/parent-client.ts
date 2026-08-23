/**
 * Parent Dashboard API Client
 * Type-safe client for parent multi-student management endpoints
 */

import { supabase } from '@/lib/supabase';

const BRAIN_URL = "/brain";

/** Parent accounts use Supabase bearer auth; student cookies remain automatic. */
async function getAuthHeaders(): Promise<Record<string, string>> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ── Types ─────────────────────────────────────────────────────────────────────

export interface StudentSummary {
  id: string;
  name: string;
  email: string;
  grade_level: string;
  interests: string[];
  created_at: string;
  last_active: string | null;
}

export interface AddStudentRequest {
  name: string;
  username: string;
  pin: string;
  grade_level?: string;
  interests?: string[];
  privacy_consent: boolean;
  privacy_notice_version?: string;
}

export interface UpdateStudentRequest {
  name?: string;
  grade_level?: string;
  interests?: string[];
}

export interface StudentProgress {
  student_id: string;
  student_name: string;
  total_credits: number;
  lessons_completed: number;
  books_finished: number;
  projects_sealed: number;
  last_activity: string | null;
  active_track: string | null;
  grade_level: string;
  interests: string[];
  learning: {
    current_learning: Array<{
      id: string;
      title: string;
      description: string;
      track: string;
      canonical_slug?: string;
      next_action?: string;
      success_criteria?: string[];
    }>;
    coverage: {
      mastered: number;
      total_required: number;
      remaining: number;
      subjects: Array<{ subject: string; mastered: number; remaining: number; required: number; scheduled: number }>;
    };
    graduation_progress: {
      total_required?: number;
      total_earned?: number;
      credits_remaining?: number;
      is_high_school?: boolean;
    };
    credit_gaps: Array<{ bucket: string; required: number; earned: number; remaining: number; priority: number }>;
    areas_to_explore: Array<{
      standard_id: string;
      subject: string;
      description: string;
      proficiency: 'NOT_STARTED' | 'DEVELOPING' | 'APPROACHING' | 'UNDERSTANDING' | 'EXTENDING';
    }>;
    placement: Record<string, unknown>;
  } | null;
}

export interface FamilyDashboard {
  parent_id: string;
  total_students: number;
  students: StudentProgress[];
  family_total_credits: number;
  recent_activity: Array<{
    student_id: string;
    student_name: string;
    lesson_id: string;
    track: string;
    title: string;
    completed_at: string | null;
  }>;
  family_investigation: ({
    title: string;
    description: string;
    track?: string;
    next_action?: string;
    success_criteria?: string[];
    participants: string[];
  } & Record<string, unknown>) | null;
}

export interface ParentAdelineTurn {
  role: 'parent' | 'adeline';
  content: string;
}

// ── API Functions ─────────────────────────────────────────────────────────────

export async function listStudents(): Promise<StudentSummary[]> {
  const res = await fetch(`${BRAIN_URL}/api/parent/students`, {
    headers: await getAuthHeaders(),
    credentials: 'include', // Important: sends auth cookies
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`listStudents failed: ${res.status}`);
  return res.json();
}

export async function addStudent(payload: AddStudentRequest): Promise<StudentSummary> {
  const res = await fetch(`${BRAIN_URL}/api/parent/students`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(await getAuthHeaders()) },
    credentials: 'include', // Important: sends auth cookies
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || `addStudent failed: ${res.status}`);
  }
  return res.json();
}

export interface ClaimStudentResponse {
  student_id: string;
  display_name: string;
  username: string;
  xp: number;
  grade_level: string;
}

export async function claimStudent(code: string, privacyConsent: boolean): Promise<ClaimStudentResponse> {
  const res = await fetch(`${BRAIN_URL}/students/claim`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(await getAuthHeaders()) },
    credentials: 'include',
    body: JSON.stringify({ code, privacy_consent: privacyConsent, privacy_notice_version: '2026-08-23' }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || 'Could not link that code.');
  }
  return res.json();
}

export async function getFamilyDashboard(): Promise<FamilyDashboard> {
  const res = await fetch(`${BRAIN_URL}/api/parent/dashboard`, {
    headers: await getAuthHeaders(),
    credentials: 'include', // Important: sends auth cookies
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`getFamilyDashboard failed: ${res.status}`);
  return res.json();
}

export async function askParentAdeline(
  message: string,
  conversationHistory: ParentAdelineTurn[] = [],
): Promise<string> {
  const res = await fetch(`${BRAIN_URL}/api/parent/adeline`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...(await getAuthHeaders()) },
    credentials: 'include',
    body: JSON.stringify({
      message,
      conversation_history: conversationHistory.slice(-10),
    }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Parent Adeline failed: ${res.status}`);
  }
  const body = await res.json();
  return body.response;
}

export async function updateStudent(
  studentId: string,
  payload: UpdateStudentRequest
): Promise<{ message: string }> {
  const res = await fetch(`${BRAIN_URL}/api/parent/students/${encodeURIComponent(studentId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...(await getAuthHeaders()) },
    credentials: 'include', // Important: sends auth cookies
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`updateStudent failed: ${res.status}`);
  return res.json();
}

export async function removeStudent(studentId: string): Promise<{ message: string }> {
  const res = await fetch(`${BRAIN_URL}/api/parent/students/${encodeURIComponent(studentId)}`, {
    method: "DELETE",
    headers: await getAuthHeaders(),
    credentials: 'include', // Important: sends auth cookies
  });
  if (!res.ok) throw new Error(`removeStudent failed: ${res.status}`);
  return res.json();
}
