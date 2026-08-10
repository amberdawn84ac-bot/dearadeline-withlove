export type PlayerProfile = {
  id: string;
  username: string;
  display_name: string;
  grade_level?: string;
};

export type StudentAuthResponse = {
  token: string;
  student_id: string;
  user: PlayerProfile;
};

const TOKEN_KEY = "adeline_token";
const STUDENT_ID_KEY = "adeline_student_id";
const PLAYER_KEY = "adeline_player";

export class StudentAuthError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "StudentAuthError";
    this.status = status;
  }
}

export function savePlayerSession(session: StudentAuthResponse) {
  localStorage.setItem(TOKEN_KEY, session.token);
  localStorage.setItem(STUDENT_ID_KEY, session.student_id);
  localStorage.setItem(PLAYER_KEY, JSON.stringify(session.user));
}

export function getPlayerSession() {
  if (typeof window === "undefined") return null;

  const token = localStorage.getItem(TOKEN_KEY);
  const studentId = localStorage.getItem(STUDENT_ID_KEY);
  const rawPlayer = localStorage.getItem(PLAYER_KEY);
  if (!token || !studentId || !rawPlayer) return null;

  try {
    return {
      token,
      studentId,
      player: JSON.parse(rawPlayer) as PlayerProfile,
    };
  } catch {
    clearPlayerSession();
    return null;
  }
}

export function clearPlayerSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(STUDENT_ID_KEY);
  localStorage.removeItem(PLAYER_KEY);
}

export async function authenticateStudent(
  mode: "login" | "register",
  body: Record<string, string>,
) {
  const response = await fetch(`/api/brain/auth/student/${mode}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await response.json().catch(() => ({}));

  if (!response.ok) {
    const detail = payload.detail;
    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) => (typeof item?.msg === "string" ? item.msg.replace(/^Value error,\s*/i, "") : ""))
        .filter(Boolean);
      throw new StudentAuthError(messages.join(" ") || "Please check the information and try again.", response.status);
    }
    throw new StudentAuthError(
      typeof detail === "string"
        ? detail
        : typeof payload.error === "string"
          ? payload.error
          : "Adeline could not sign you in.",
      response.status,
    );
  }

  return payload as StudentAuthResponse;
}
