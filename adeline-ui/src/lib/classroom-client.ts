import { supabase } from './supabase';

export const TRACKS = {
  CREATION_SCIENCE: 'Science & Creation', HEALTH_NATUROPATHY: 'Health & Natural Medicine',
  HOMESTEADING: 'Land & Self-Sufficiency', GOVERNMENT_ECONOMICS: 'Civics & Economics',
  JUSTICE_CHANGEMAKING: 'Justice & Social Change', DISCIPLESHIP: 'Faith & Character',
  TRUTH_HISTORY: 'History & Truth', ENGLISH_LITERATURE: 'Language & Literature',
  APPLIED_MATHEMATICS: 'Real-World Mathematics', CREATIVE_ECONOMY: 'Creative Economy',
} as const;
export type ClassroomTrack = keyof typeof TRACKS;
export type ClassroomRequest = { topic: string; track: ClassroomTrack; level: string; targets: string[]; materials: string; action: 'plan' | 'build' };
export type SceneType = 'slide' | 'interactive' | 'quiz' | 'pbl';
type Variable = { label: string; unit: string; minimum: number; maximum: number; initial: number; step: number };
export type SceneMaterial = { id: string; kind: 'text' | 'link' | 'image'; title: string; content?: string; url?: string; image_url?: string; attribution?: string; license_url?: string };
export type ClassroomScene = {
  id: string; title: string; type: SceneType; content: string; key_points: string[];
  actions: { role_id: string; text: string }[]; learner_task: string; success_criteria: string[];
  family_roles: Record<'elementary' | 'middle' | 'high_school', string>;
  question: { prompt: string; choices: { id: string; label: string }[] } | null;
  simulation: { model: 'proportional' | 'rectangle_area' | 'mixture_fraction'; x: Variable; y: Variable; output_label: string; output_unit: string; explanation: string; prediction_prompt: string; observation_prompt: string } | null;
  materials: string[]; steps: string[]; resources?: SceneMaterial[];
};
export type Blueprint = { title: string; understanding: string; essential_question: string; demonstration: string; integrated_tracks: ClassroomTrack[]; next_revisit: string; roster: { id: string; name: string; role: string; persona: string }[]; scenes?: { id: string; title: string; type: SceneType; objective: string; brief: string }[] };
export type Feedback = { saved: boolean; review: string; correct?: boolean };
export type ClassroomState = { id?: string; request?: ClassroomRequest; phase: 'planned' | 'building' | 'ready' | 'failed'; title: string; built_scenes?: number; error?: string; plan?: Blueprint; classroom?: { blueprint: Blueprint; scenes: ClassroomScene[] }; responses?: Record<string, { text: string; feedback: Feedback }>; dialogue?: Record<string, ClassroomTurn[]> };

async function request<T>(student: string, item: string, body?: unknown, suffix = ''): Promise<T> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  const response = await fetch(`/brain/classroom/${encodeURIComponent(student)}/${encodeURIComponent(item)}${suffix}`, {
    method: body === undefined ? 'GET' : 'POST', credentials: 'include', cache: 'no-store',
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  if (response.status === 404 && body === undefined) return null as T;
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(typeof error.detail === 'string' ? error.detail : 'Your exploration could not be opened.');
  }
  return response.json();
}
export const getClassroom = (student: string, item: string) => request<ClassroomState | null>(student, item);
export const prepareClassroom = (student: string, item: string, body: ClassroomRequest) => request<ClassroomState>(student, item, body);
export const submitClassroomResponse = (student: string, item: string, scene_id: string, text: string, submission_key: string) => request<Feedback>(student, item, { scene_id, text, submission_key }, '/responses');
export type ClassroomTurn = { key: string; question: string; answer: string; teaching_move: string };
export const talkToClassroom = (student: string, item: string, scene_id: string, message: string, submission_key: string) => request<ClassroomTurn>(student, item, { scene_id, message, submission_key }, '/conversation');
export const listClassrooms = (student: string) => request<Array<{ item_id: string; title: string; phase: string }>>(student, '');

export const getSceneMaterials = (student: string, item: string, scene_id: string) => request<SceneMaterial[]>(student, item, { scene_id }, '/materials');
