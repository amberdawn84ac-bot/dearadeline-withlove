import { supabase } from '@/lib/supabase';
const BASE = '/brain/curriculum';

async function request<T>(path: string, body?: unknown, method?: string): Promise<T> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  const response = await fetch(`${BASE}${path}`, {
    method: method ?? (body === undefined ? 'GET' : 'POST'),
    credentials: 'include', cache: 'no-store',
    headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  if (!response.ok) throw new Error(`Could not save or load curriculum record (${response.status})`);
  return response.json();
}

export interface EvidenceAttempt {
  id: string; lessonId: string; canonicalSlug: string; canonicalRevision: string;
  kind: string; content: { text?: string; [key: string]: unknown }; parentAttemptId?: string;
}
export interface CurrentUnit {
  id: string; title: string; unitId: string; experienceId: string | null;
  canonicalTopic: string | null; track: string | null;
}
export const getFamilyUnit = (household: string) => request<{ current: CurrentUnit | null; upcoming: Array<{ id: string; title: string }> }>(`/households/${encodeURIComponent(household)}/unit`);
export const completeUnitExperience = (household: string, queue: string, experience: string) => request(`/households/${encodeURIComponent(household)}/units/${encodeURIComponent(queue)}/experiences/${encodeURIComponent(experience)}/complete`, {});
export const advanceFamilyUnit = (household: string, queue: string) => request(`/households/${encodeURIComponent(household)}/units/${encodeURIComponent(queue)}/advance`, {});
export const getEvidencePortfolio = (student: string) => request<{ attempts: EvidenceAttempt[]; evaluations: unknown[] }>(`/students/${encodeURIComponent(student)}/portfolio`);
export const saveEvidenceNote = (student: string, body: { canonical_slug: string; canonical_revision?: string; lesson_id: string; parent_attempt_id?: string; kind: 'note' | 'revision'; content: { text: string; label: string }; submission_key: string }) => request<EvidenceAttempt>(`/students/${encodeURIComponent(student)}/evidence`, body);
export interface StudentCharacter { name: string; identity: string; role_preferences: string[]; persistent_traits: string[]; visual_data: Record<string, unknown> }
export const saveStudentCharacter = (student: string, body: StudentCharacter) => request(`/students/${encodeURIComponent(student)}/character`, body, 'PUT');
export const getStudentCharacter = (student: string) => request<{ name: string; identity: string; rolePreferences: string[] | string; persistentTraits: string[] | string; visualData: Record<string, unknown> } | null>(`/students/${encodeURIComponent(student)}/character`);
export const enqueueFamilyUnit = (household: string, title: string, experiences: Array<{canonical_topic:string;track:string}>) => request(`/households/${encodeURIComponent(household)}/units`, {title,experiences});
export const evaluateEvidence = (student: string, attempt: string, skillId: string, result: 'developing'|'demonstrated'|'secure', reasoning: string) => request(`/students/${encodeURIComponent(student)}/evidence/${encodeURIComponent(attempt)}/evaluate`, {skill_id:skillId,result,reasoning});
export interface TimelineCard {id:string;dateStart:string;dateEnd?:string;claim:string;studentName:string;uncertainty:string;sources:Array<{url?:string}>;omittedPerspectives:string[]}
export const getFamilyTimeline = (household:string) => request<TimelineCard[]>(`/households/${encodeURIComponent(household)}/timeline`);
export const saveTimelineCard = (student:string,attempt:EvidenceAttempt,card:{date_start:string;date_end?:string;claim:string;sources:Array<{url:string}>;omitted_perspectives:string[];uncertainty:string}) => request(`/students/${encodeURIComponent(student)}/evidence`, {canonical_slug:attempt.canonicalSlug,canonical_revision:attempt.canonicalRevision,lesson_id:attempt.lessonId,parent_attempt_id:attempt.id,kind:'timeline',content:card,submission_key:crypto.randomUUID()});
