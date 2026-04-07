/**
 * Parent Dashboard API Client
 * Type-safe client for parent multi-student management endpoints
 */

const BRAIN_URL = "/brain";

function getAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("auth_token");
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }
  return headers;
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
  email: string;
  grade_level?: string;
  interests?: string[];
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
    completed_at: string | null;
  }>;
}

// ── API Functions ─────────────────────────────────────────────────────────────

export async function listStudents(): Promise<StudentSummary[]> {
  const res = await fetch(`${BRAIN_URL}/api/parent/students`, {
    headers: getAuthHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`listStudents failed: ${res.status}`);
  return res.json();
}

export async function addStudent(payload: AddStudentRequest): Promise<StudentSummary> {
  const res = await fetch(`${BRAIN_URL}/api/parent/students`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({}));
    throw new Error(error.detail || `addStudent failed: ${res.status}`);
  }
  return res.json();
}

export async function getFamilyDashboard(): Promise<FamilyDashboard> {
  const res = await fetch(`${BRAIN_URL}/api/parent/dashboard`, {
    headers: getAuthHeaders(),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`getFamilyDashboard failed: ${res.status}`);
  return res.json();
}

export async function updateStudent(
  studentId: string,
  payload: UpdateStudentRequest
): Promise<{ message: string }> {
  const res = await fetch(`${BRAIN_URL}/api/parent/students/${encodeURIComponent(studentId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`updateStudent failed: ${res.status}`);
  return res.json();
}

export async function removeStudent(studentId: string): Promise<{ message: string }> {
  const res = await fetch(`${BRAIN_URL}/api/parent/students/${encodeURIComponent(studentId)}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });
  if (!res.ok) throw new Error(`removeStudent failed: ${res.status}`);
  return res.json();
}
