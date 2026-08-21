export const dynamic = 'force-dynamic';

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  // Middleware validates either the Brain student cookie or the parent/admin
  // Supabase session. Requiring only auth_token here locked valid parents out.
  return <>{children}</>;
}
