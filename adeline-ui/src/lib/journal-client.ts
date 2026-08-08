import { supabase } from '@/lib/supabase';
import type { SketchnoteData } from '@/components/SketchnoteCard';

export type DailyJournalNote = {
  id: string;
  topic: string;
  track: string;
  learned: string;
  action: string | null;
  note: SketchnoteData | null;
  source: string;
  created_at: string | null;
};

async function headers() {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

function noteAsText(note: SketchnoteData) {
  const sections = (note.sections ?? []).map((section) => `${section.heading}: ${section.text}`).join('\n');
  return [
    note.big_idea,
    sections,
    note.keywords?.length ? `Keywords: ${note.keywords.join(', ')}` : '',
    note.footer,
  ].filter(Boolean).join('\n\n');
}

export async function saveSketchnote(studentId: string, note: SketchnoteData) {
  const res = await fetch('/brain/journal/entries', {
    method: 'POST',
    headers: await headers(),
    body: JSON.stringify({
      student_id: studentId,
      topic: note.title,
      track: note.track || 'ENGLISH_LITERATURE',
      learned: noteAsText(note),
      action: 'Saved from a conversation with Adeline',
      note,
      source: 'adeline_sketchnote',
    }),
    cache: 'no-store',
  });
  if (!res.ok) throw new Error(`journal save failed: ${res.status}`);
  return res.json();
}

export async function listDailyJournalNotes(studentId: string, limit = 80): Promise<DailyJournalNote[]> {
  const res = await fetch(`/brain/journal/entries/${encodeURIComponent(studentId)}?limit=${limit}`, {
    headers: await headers(),
    cache: 'no-store',
  });
  if (!res.ok) throw new Error(`journal list failed: ${res.status}`);
  const data = await res.json() as { notes: DailyJournalNote[] };
  return data.notes;
}
