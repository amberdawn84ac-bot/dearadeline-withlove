'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { useStudent } from '@/lib/useStudent';
import { PersistentAdeline } from '@/components/PersistentAdeline';
import styles from './sites-dashboard.module.css';

const NAV_ITEMS = [
  ['☀', 'Today', '/dashboard'],
  ['✦', 'Learning Plan', '/dashboard/journey'],
  ['⚒', 'Project Workshop', '/dashboard/projects'],
  ['▧', 'Portfolio', '/dashboard/portfolio'],
  ['▤', 'Reading Nook', '/dashboard/reading-nook'],
  ['☆', 'Opportunities', '/dashboard/opportunities'],
  ['⚙', 'Settings', '/dashboard/settings'],
] as const;

export function AppSidebar({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { student } = useStudent();
  const [profileOpen, setProfileOpen] = useState(false);
  const [dailyBread, setDailyBread] = useState<{ verse: string; reference: string; bigIdea: string; practice: string } | null>(null);

  useEffect(() => {
    let cancelled = false;
    void fetch('/brain/daily-bread')
      .then((response) => response.ok ? response.json() : null)
      .then((data) => { if (!cancelled && data?.verse) setDailyBread(data); })
      .catch(() => undefined);
    return () => { cancelled = true; };
  }, []);

  const initial = (student?.name?.trim()?.[0] || 'A').toUpperCase();

  const isActive = (href: string) => {
    const clean = href.split('#')[0];
    if (clean === '/dashboard') return pathname === '/dashboard';
    return pathname === clean || pathname.startsWith(`${clean}/`);
  };

  async function signOut() {
    await fetch('/api/student-auth', { method: 'DELETE' }).catch(() => undefined);
    router.replace('/login');
    router.refresh();
  }

  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <Link href="/dashboard" className={styles.brand}>Dear Adeline</Link>
        <div className={styles.profileWrap}>
          <button
            type="button"
            className={styles.profileButton}
            onClick={() => setProfileOpen((open) => !open)}
            aria-label="Student profile"
            aria-expanded={profileOpen}
          >
            {initial}
          </button>
          {profileOpen && (
            <div className={styles.profileMenu}>
              <p>{student?.name || 'Dear Adeline student'}</p>
              <button type="button" onClick={signOut}>Sign out</button>
            </div>
          )}
        </div>
      </header>

      <PersistentAdeline />

      <div className={styles.body}>
        <aside className={styles.sidebar} aria-label="Dashboard menu">
          <nav className={styles.menu}>
            {NAV_ITEMS.map(([icon, label, href]) => (
              <Link key={`${label}-${href}`} href={href} data-active={isActive(href)}>
                <b>{icon}</b><span>{label}</span>
              </Link>
            ))}
          </nav>

          <article className={styles.dailyBread}>
            <div className={styles.breadHeading}><span>DAILY BREAD</span><b>❦</b></div>
            <blockquote>“{dailyBread?.verse || 'Open today’s passage and receive the text in context.'}”</blockquote>
            <cite>{dailyBread?.reference || 'Today’s Scripture'}</cite>
            <hr />
            <p>{dailyBread?.bigIdea || 'A new family Bible lesson is ready each day.'}</p>
            <strong>Today&apos;s practice</strong>
            <em>{dailyBread?.practice || 'Read, understand, and live the passage today.'}</em>
            <Link href="/dashboard/daily-bread" className="mt-4 inline-flex rounded-lg bg-[#2F4731] px-3 py-2 text-xs font-bold text-white">
              Start Deep Dive Study →
            </Link>
          </article>
        </aside>

        <main className={styles.content}>{children}</main>
      </div>
    </div>
  );
}
