import { redirect } from 'next/navigation';
import { cookies } from 'next/headers';

export const dynamic = 'force-dynamic';

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  const cookieStore = await cookies();
  const studentToken = cookieStore.get('auth_token')?.value;

  // Middleware validates the token before this layout renders. This second
  // check prevents accidental exposure if middleware configuration changes.
  if (!studentToken) {
    redirect('/login');
  }

  return <>{children}</>;
}
