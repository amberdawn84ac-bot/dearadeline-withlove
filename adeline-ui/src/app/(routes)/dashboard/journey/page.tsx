import { redirect } from 'next/navigation';

// The detailed year map belongs to the planning engine and parent dashboard.
// Keep the former URL working for bookmarks and previously generated links.
export default function FormerStudentLearningPlanPage() {
  redirect('/dashboard');
}
