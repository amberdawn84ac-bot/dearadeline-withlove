'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useState } from 'react';
import { useStudent } from '@/lib/useStudent';
import styles from './sites-dashboard.module.css';

const NAV_ITEMS = [
  ['☀', 'Today', '/dashboard'],
  ['♡', 'Talk to Adeline', '/dashboard#talk-to-adeline'],
  ['✦', 'Learning Plan', '/dashboard/journey'],
  ['⚒', 'Project Workshop', '/dashboard/projects'],
  ['▧', 'Portfolio', '/dashboard/portfolio'],
  ['◎', 'Transcript & Graduation', '/dashboard/transcript'],
  ['▤', 'Reading Nook', '/dashboard/reading-nook'],
  ['⚙', 'Settings', '/dashboard/settings'],
] as const;

export function AppSidebar({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { student } = useStudent();
  const [profileOpen, setProfileOpen] = useState(false);

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
        <span className={styles.headerLabel}>Today&apos;s Adventure</span>
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
            <blockquote>“The beginning of wisdom is this: Get wisdom.”</blockquote>
            <cite>Proverbs 4:7</cite>
            <hr />
            <p>Wisdom begins when you are willing to notice what you do not yet know.</p>
            <strong>Today&apos;s practice</strong>
            <em>Ask one honest question and follow it.</em>
          </article>
        </aside>

        <main className={styles.content}>{children}</main>
      </div>
    </div>
  );
}
