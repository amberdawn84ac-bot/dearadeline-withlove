'use client';

import { FormEvent, Suspense, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { supabase } from '@/lib/supabase';
import { setAuthCookie } from '@/lib/auth-cookies';

const ADELINE_FACE = '/adeline-face.webp';

type Mode = 'login' | 'register';

function playerKey(name: string) {
  const normalized = name.trim().toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '').slice(0, 20);
  return normalized.length >= 3 ? normalized : `${normalized || 'new'}_player`.slice(0, 20);
}

function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const invitationCode = searchParams.get('invite')?.replace(/[^a-z0-9]/gi, '').toUpperCase() ?? '';
  const isParentInvitation = searchParams.get('parent') === '1' && invitationCode.length >= 6;
  const [audience, setAudience] = useState<'student' | 'parent'>(searchParams.get('parent') === '1' ? 'parent' : 'student');
  const [mode, setMode] = useState<Mode>(searchParams.get('mode') === 'register' || isParentInvitation ? 'register' : 'login');
  const [username, setUsername] = useState('');
  const [pin, setPin] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [gradeLevel, setGradeLevel] = useState('PLACEMENT');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [parentName, setParentName] = useState('');
  const [learnerParentName, setLearnerParentName] = useState('');
  const [learnerParentEmail, setLearnerParentEmail] = useState('');
  const [verificationSent, setVerificationSent] = useState(false);
  const [invitePrivacyConsent, setInvitePrivacyConsent] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [pendingInvite, setPendingInvite] = useState(invitationCode);

  useEffect(() => {
    if (audience === 'parent') return;
    fetch('/api/student-auth', { cache: 'no-store' })
      .then((response) => {
        if (response.ok) router.replace('/dashboard');
      })
      .catch(() => undefined);
  }, [audience, router]);

  useEffect(() => {
    if (invitationCode) {
      window.localStorage.setItem('adeline_parent_invite', invitationCode);
      setPendingInvite(invitationCode);
      return;
    }
    const saved = window.localStorage.getItem('adeline_parent_invite') ?? '';
    if (/^[A-Z0-9]{6,32}$/.test(saved)) setPendingInvite(saved);
  }, [invitationCode]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError('');

    try {
      if (audience === 'parent') {
        if (pendingInvite) window.localStorage.setItem('adeline_parent_invite', pendingInvite);
        const emailRedirectTo = pendingInvite
          ? `${window.location.origin}/login?parent=1&mode=login&invite=${encodeURIComponent(pendingInvite)}`
          : `${window.location.origin}/login?parent=1&mode=login`;
        const authResult = mode === 'register'
          ? await supabase.auth.signUp({
              email: email.trim(), password,
              options: { emailRedirectTo, data: { name: parentName.trim() } },
            })
          : await supabase.auth.signInWithPassword({ email: email.trim(), password });
        if (authResult.error) throw authResult.error;
        const session = authResult.data.session;
        if (!session) {
          throw new Error('Check your email to confirm the account, then return to sign in.');
        }
        await setAuthCookie(session.access_token);
        const bootstrap = await fetch('/brain/auth/parent/bootstrap', {
          method: 'POST',
          headers: { Authorization: `Bearer ${session.access_token}`, 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: parentName.trim() || email.split('@')[0] || 'Parent' }),
        });
        const bootstrapBody = await bootstrap.json().catch(() => ({}));
        if (!bootstrap.ok) throw new Error(bootstrapBody.detail || 'Could not open the family account.');
        if (pendingInvite) {
          if (!invitePrivacyConsent) throw new Error('Please review the Children’s Privacy Notice and confirm parental consent.');
          const claim = await fetch('/brain/students/claim', {
            method: 'POST',
            headers: { Authorization: `Bearer ${session.access_token}`, 'Content-Type': 'application/json' },
            body: JSON.stringify({ code: pendingInvite, privacy_consent: true, privacy_notice_version: '2026-08-23' }),
          });
          const claimBody = await claim.json().catch(() => ({}));
          if (!claim.ok) throw new Error(claimBody.detail || 'Your parent account was created, but the learner invitation could not be linked.');
          window.localStorage.removeItem('adeline_parent_invite');
        }
        router.push('/dashboard/parent');
        router.refresh();
        return;
      }
      const body: Record<string, string> = {
        mode,
        username: playerKey(mode === 'register' ? displayName : username),
        pin,
      };
      if (mode === 'register') {
        body.display_name = displayName.trim();
        body.grade_level = gradeLevel;
        body.parent_name = learnerParentName.trim();
        body.parent_email = learnerParentEmail.trim();
      }

      const response = await fetch('/api/student-auth', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        const detail = Array.isArray(data?.detail)
          ? data.detail.map((item: { msg?: string }) => item?.msg).filter(Boolean).join(' ')
          : data?.detail;
        throw new Error(detail || 'Adeline could not sign you in.');
      }

      if (data.requires_parent_verification) {
        setVerificationSent(true);
        return;
      }

      router.push('/dashboard');
      router.refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Adeline could not sign you in.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="min-h-screen grid place-items-center px-4 py-8 bg-[radial-gradient(circle_at_20%_10%,rgba(214,166,75,.18),transparent_34%),radial-gradient(circle_at_85%_85%,rgba(51,99,71,.16),transparent_36%)] bg-[#f7f1e6] text-[#263b2d]">
      {verificationSent ? <section className="w-full max-w-[520px] rounded-[30px] border border-[#374f3c2e] bg-[#fffdf7] p-8 text-center shadow-[0_24px_70px_rgba(57,48,34,.13)]"><p className="text-4xl">✉️</p><h1 className="mt-4 text-3xl font-bold text-[#294832]">A parent needs to approve this account</h1><p className="mt-3 text-sm leading-6 text-[#667064]">We sent the parent or guardian a private review link. Learning access stays closed until they approve it. The link expires in 72 hours.</p><Link href="/privacy" className="mt-5 inline-flex font-bold text-[#9A3F4A] underline">Read the Children&rsquo;s Privacy Notice</Link></section> :
      <section className="w-full max-w-[520px] rounded-[30px] border border-[#374f3c2e] bg-[#fffdf7f0] p-7 sm:p-9 shadow-[0_24px_70px_rgba(57,48,34,.13)]">
        <Link href="/" className="text-[13px] font-black text-[#49654e] no-underline">
          ← Dear Adeline
        </Link>

        <div className="my-6 flex items-center gap-4">
          <img
            src={ADELINE_FACE}
            alt="Adeline"
            className="h-[82px] w-[82px] rounded-full border-4 border-[#d6b15c] bg-[#f4ead5] object-cover object-[center_25%]"
          />
          <div>
            <p className="mb-1 text-[10px] font-black uppercase tracking-[.11em] text-[#9c623e]">
              Welcome to your learning adventure
            </p>
            <h1
              className="m-0 text-[38px] leading-none font-normal text-[#294832]"
              style={{ fontFamily: 'var(--font-emilys-candy), "Emilys Candy", cursive' }}
            >
              {mode === 'login' ? 'Come on in!' : 'Create your player'}
            </h1>
          </div>
        </div>

        <div className="mb-6 grid grid-cols-2 gap-1 rounded-[15px] bg-[#eae2d2] p-[5px]">
          <button
            type="button"
            onClick={() => { setMode('login'); setError(''); }}
            className={`min-h-[43px] rounded-[11px] border-0 font-black ${mode === 'login' ? 'bg-[#fffdf7] text-[#294832] shadow-sm' : 'bg-transparent text-[#667064]'}`}
          >
            Sign in
          </button>
          <button
            type="button"
            onClick={() => { setMode('register'); setError(''); }}
            className={`min-h-[43px] rounded-[11px] border-0 font-black ${mode === 'register' ? 'bg-[#fffdf7] text-[#294832] shadow-sm' : 'bg-transparent text-[#667064]'}`}
          >
            New player
          </button>
        </div>

        <button
          type="button"
          onClick={() => { setAudience(audience === 'student' ? 'parent' : 'student'); setError(''); }}
          className="mb-5 w-full border-0 bg-transparent text-xs font-black text-[#49654e] underline underline-offset-4"
        >
          {audience === 'student' ? 'I am a parent or guardian' : 'Back to learner sign in'}
        </button>

        <form onSubmit={submit} className="grid gap-4">
          {audience === 'parent' && pendingInvite && (
            <div className="rounded-xl border border-[#cbdcc7] bg-[#edf4ea] px-4 py-3 text-sm text-[#2F4731]"><strong>Family invitation ready.</strong> {mode === 'register' ? 'Create your parent account' : 'Sign in'} and this learner can be connected after you confirm consent.<label className="mt-3 flex items-start gap-2 text-xs leading-5"><input type="checkbox" required checked={invitePrivacyConsent} onChange={(event) => setInvitePrivacyConsent(event.target.checked)} className="mt-0.5 h-4 w-4 accent-[#BD6809]" /><span>I am this learner&rsquo;s parent or legal guardian and consent after reviewing the <Link href="/privacy" target="_blank" className="font-bold underline">Children&rsquo;s Privacy Notice</Link>.</span></label></div>
          )}
          {audience === 'parent' && mode === 'register' && (
            <label className="grid gap-2 text-xs font-black text-[#3c5140]">
              Your name
              <input required autoComplete="name" value={parentName} onChange={(event) => setParentName(event.target.value)} className="min-h-[49px] rounded-[13px] border border-[#d7cdbb] bg-[#fffefa] px-3" />
            </label>
          )}
          {audience === 'parent' && (
            <>
              <label className="grid gap-2 text-xs font-black text-[#3c5140]">
                Parent email
                <input required type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} className="min-h-[49px] rounded-[13px] border border-[#d7cdbb] bg-[#fffefa] px-3" />
              </label>
              <label className="grid gap-2 text-xs font-black text-[#3c5140]">
                Password
                <input required type="password" minLength={8} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} value={password} onChange={(event) => setPassword(event.target.value)} className="min-h-[49px] rounded-[13px] border border-[#d7cdbb] bg-[#fffefa] px-3" />
              </label>
            </>
          )}
          {audience === 'student' && <>
          {mode === 'register' && (
            <>
              <label className="grid gap-2 text-xs font-black text-[#3c5140]">
                What should Adeline call you?
                <input
                  required
                  autoComplete="name"
                  value={displayName}
                  onChange={(event) => setDisplayName(event.target.value)}
                  className="min-h-[49px] rounded-[13px] border border-[#d7cdbb] bg-[#fffefa] px-3 text-[#243429] outline-none focus:border-[#6e8a68] focus:ring-4 focus:ring-[#6e8a6826]"
                />
              </label>
              <label className="grid gap-2 text-xs font-black text-[#3c5140]">
                Learning level
                <select
                  value={gradeLevel}
                  onChange={(event) => setGradeLevel(event.target.value)}
                  className="min-h-[49px] rounded-[13px] border border-[#d7cdbb] bg-[#fffefa] px-3 text-[#243429] outline-none"
                >
                  <option value="PLACEMENT">Not sure — let Adeline discover it</option>
                  <option value="K">Kindergarten</option>
                  {Array.from({ length: 12 }, (_, index) => <option key={index + 1} value={String(index + 1)}>Grade {index + 1}</option>)}
                </select>
              </label>
              <div className="rounded-xl border border-[#d7cdbb] bg-[#f7f1e6] p-4">
                <p className="text-xs font-black text-[#3c5140]">Parent or guardian approval</p>
                <p className="mt-1 text-[11px] leading-5 text-[#667064]">A learner account stays locked until a parent reviews the privacy notice and approves it by email.</p>
                <label className="mt-3 grid gap-2 text-xs font-black text-[#3c5140]">Parent or guardian name<input required autoComplete="name" value={learnerParentName} onChange={(event) => setLearnerParentName(event.target.value)} className="min-h-[45px] rounded-[11px] border border-[#d7cdbb] bg-[#fffefa] px-3" /></label>
                <label className="mt-3 grid gap-2 text-xs font-black text-[#3c5140]">Parent or guardian email<input required type="email" autoComplete="email" value={learnerParentEmail} onChange={(event) => setLearnerParentEmail(event.target.value)} className="min-h-[45px] rounded-[11px] border border-[#d7cdbb] bg-[#fffefa] px-3" /></label>
                <Link href="/privacy" target="_blank" className="mt-3 inline-flex text-[11px] font-bold text-[#9A3F4A] underline">Children&rsquo;s Privacy Notice</Link>
              </div>
            </>
          )}

          {mode === 'login' && <label className="grid gap-2 text-xs font-black text-[#3c5140]">
            What does Adeline call you?
            <input
              required
              autoComplete="username"
              maxLength={100}
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              className="min-h-[49px] rounded-[13px] border border-[#d7cdbb] bg-[#fffefa] px-3 text-[#243429] outline-none focus:border-[#6e8a68] focus:ring-4 focus:ring-[#6e8a6826]"
            />
          </label>}

          <label className="grid gap-2 text-xs font-black text-[#3c5140]">
            4-digit PIN
            <input
              required
              type="password"
              inputMode="numeric"
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              pattern="[0-9]{4}"
              maxLength={4}
              value={pin}
              onChange={(event) => setPin(event.target.value.replace(/\D/g, '').slice(0, 4))}
              className="min-h-[49px] rounded-[13px] border border-[#d7cdbb] bg-[#fffefa] px-3 text-[#243429] outline-none focus:border-[#6e8a68] focus:ring-4 focus:ring-[#6e8a6826]"
            />
          </label>
          </>}

          {error && <p className="m-0 rounded-xl bg-[#fae2dc] px-3 py-2 text-xs font-bold text-[#8a352b]">{error}</p>}

          <button
            type="submit"
            disabled={busy}
            className="mt-1 min-h-[52px] rounded-[15px] border-0 bg-[#66845e] font-black text-white shadow-[0_8px_20px_rgba(72,103,68,.22)] disabled:opacity-60"
          >
            {busy ? 'Opening your adventure…' : mode === 'login' ? 'Enter Dear Adeline' : audience === 'parent' ? 'Create family account' : 'Start my adventure'}
          </button>
        </form>

        <p className="mt-6 text-center text-[11px] leading-relaxed text-[#73786f]">
          {audience === 'parent' ? 'One family account securely connects siblings while preserving each learner’s own plan and evidence.' : 'One student identity keeps learning, projects, games, portfolio work, and graduation progress together.'}
        </p>
      </section>}
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#f7f1e6]" />}>
      <LoginContent />
    </Suspense>
  );
}
