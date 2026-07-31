# Adeline World — Plan 1: Foundation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Set up Supabase DB schema, auth (parent signup/login, child profiles, guest mode), and React Router navigation so the app knows who is playing before any game content loads.

**Architecture:** The existing Express + React + Vite app gets Supabase Auth wired in via a React context. React Router replaces the current tab system. Three entry paths: guest (localStorage only), parent login → child select → game, or parent signup → create child → game. All game routes are protected — unauthenticated users see the landing/auth screen.

**Tech Stack:** React 19, Vite, Tailwind, Express, @supabase/supabase-js, react-router-dom, existing Supabase project (gyxowttfwqbajoapfebf)

---

## File Structure

```
src/
  lib/
    supabase.ts          # Supabase browser client (new)
  types/
    auth.ts              # ParentAccount, StudentProfile, GuestSession types (new)
  context/
    AuthContext.tsx      # Auth state, session management, guest mode (new)
  pages/
    LandingPage.tsx      # Entry: guest / login / signup choice (new)
    LoginPage.tsx        # Parent email+password login (new)
    SignupPage.tsx       # Parent signup + display name (new)
    ChildSelectPage.tsx  # Pick which child is playing (new)
    CreateChildPage.tsx  # Add child profile under parent account (new)
    GameShell.tsx        # Protected game wrapper, replaces App.tsx content (new)
  App.tsx                # Replace tab nav with React Router (modify)
  main.tsx               # Wrap with AuthProvider (modify)
supabase/
  migrations/
    001_initial_schema.sql  # All tables + RLS policies (new)
.env                     # Add VITE_SUPABASE_URL + VITE_SUPABASE_ANON_KEY (modify)
.env.example             # Document new VITE_ vars (modify)
```

---

## Task 1: Install Dependencies

**Files:**
- Modify: `package.json` (via npm install)

- [ ] **Step 1: Install Supabase client and React Router**

```bash
cd /c/Users/Aarons/Adelinemobile
npm install @supabase/supabase-js react-router-dom
```

Expected output ends with: `found 0 vulnerabilities`

- [ ] **Step 2: Verify installs**

```bash
node -e "require('@supabase/supabase-js'); require('react-router-dom'); console.log('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add package.json package-lock.json
git commit -m "deps: add supabase-js and react-router-dom"
```

---

## Task 2: Supabase Database Schema

**Files:**
- Create: `supabase/migrations/001_initial_schema.sql`

- [ ] **Step 1: Create migrations directory and schema file**

Create `supabase/migrations/001_initial_schema.sql`:

```sql
-- Parent accounts (one per Supabase auth user)
create table public.parent_accounts (
  id uuid references auth.users(id) on delete cascade primary key,
  email text not null,
  display_name text not null,
  created_at timestamptz default now() not null
);

-- Student profiles (children under a parent account)
create table public.student_profiles (
  id uuid default gen_random_uuid() primary key,
  parent_id uuid references public.parent_accounts(id) on delete cascade not null,
  display_name text not null,
  username text unique not null,
  username_approved boolean default false not null,
  age integer,
  avatar_data jsonb default '{}'::jsonb not null,
  avatar_approved boolean default false not null,
  xp integer default 0 not null,
  ade_coins integer default 100 not null,
  trading_enabled boolean default false not null,
  created_at timestamptz default now() not null
);

-- Enable Row Level Security
alter table public.parent_accounts enable row level security;
alter table public.student_profiles enable row level security;

-- RLS: parent accounts
create policy "parent_select_own"
  on public.parent_accounts for select
  using (auth.uid() = id);

create policy "parent_update_own"
  on public.parent_accounts for update
  using (auth.uid() = id);

create policy "parent_insert_own"
  on public.parent_accounts for insert
  with check (auth.uid() = id);

-- RLS: student profiles
create policy "parent_select_children"
  on public.student_profiles for select
  using (parent_id = auth.uid());

create policy "parent_insert_children"
  on public.student_profiles for insert
  with check (parent_id = auth.uid());

create policy "parent_update_children"
  on public.student_profiles for update
  using (parent_id = auth.uid());

create policy "parent_delete_children"
  on public.student_profiles for delete
  using (parent_id = auth.uid());
```

- [ ] **Step 2: Apply migration via Supabase MCP or SQL editor**

Go to: https://supabase.com/dashboard/project/gyxowttfwqbajoapfebf/sql/new

Paste the contents of `supabase/migrations/001_initial_schema.sql` and click Run.

Expected: "Success. No rows returned"

Verify tables exist:
```sql
select table_name from information_schema.tables
where table_schema = 'public'
order by table_name;
```
Expected rows include: `parent_accounts`, `student_profiles`

- [ ] **Step 3: Commit the migration file**

```bash
git add supabase/
git commit -m "db: add initial schema - parent_accounts and student_profiles with RLS"
```

---

## Task 3: Supabase Client + Environment Variables

**Files:**
- Modify: `.env`
- Modify: `.env.example`
- Create: `src/lib/supabase.ts`

- [ ] **Step 1: Add Supabase vars to .env**

Open `/c/Users/Aarons/Adelinemobile/.env` and add:

```
VITE_SUPABASE_URL=https://gyxowttfwqbajoapfebf.supabase.co
VITE_SUPABASE_ANON_KEY=sb_publishable_MmzSBzNdFZ9q16-ByBfTGQ_6VKNjc2h
```

- [ ] **Step 2: Add to .env.example**

Open `.env.example` and add:

```
# Supabase project connection (safe to use in browser — RLS enforces access control)
VITE_SUPABASE_URL=https://gyxowttfwqbajoapfebf.supabase.co
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key_here
```

- [ ] **Step 3: Create `src/lib/supabase.ts`**

```typescript
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

if (!supabaseUrl || !supabaseAnonKey) {
  throw new Error('Missing VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY in .env')
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey)
```

- [ ] **Step 4: Verify client loads**

```bash
npm run dev
```

Open browser console at http://localhost:3000. No errors should appear. Kill server with Ctrl+C.

- [ ] **Step 5: Commit**

```bash
git add src/lib/supabase.ts .env.example
git commit -m "feat: add supabase client with env config"
```

---

## Task 4: Auth Types

**Files:**
- Create: `src/types/auth.ts`

- [ ] **Step 1: Create `src/types/auth.ts`**

```typescript
export interface ParentAccount {
  id: string
  email: string
  display_name: string
  created_at: string
}

export interface StudentProfile {
  id: string
  parent_id: string
  display_name: string
  username: string
  username_approved: boolean
  age: number | null
  avatar_data: Record<string, unknown>
  avatar_approved: boolean
  xp: number
  ade_coins: number
  trading_enabled: boolean
  created_at: string
}

export interface GuestSession {
  mode: 'guest'
  displayName: string
  avatarData: Record<string, unknown>
  xp: number
  adeCoins: number
}
```

- [ ] **Step 2: Commit**

```bash
git add src/types/auth.ts
git commit -m "feat: add auth types - ParentAccount, StudentProfile, GuestSession"
```

---

## Task 5: Auth Context

**Files:**
- Create: `src/context/AuthContext.tsx`

- [ ] **Step 1: Create `src/context/AuthContext.tsx`**

```typescript
import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { Session } from '@supabase/supabase-js'
import { supabase } from '../lib/supabase'
import { ParentAccount, StudentProfile, GuestSession } from '../types/auth'

interface AuthContextType {
  session: Session | null
  parentAccount: ParentAccount | null
  children: StudentProfile[]
  activeChild: StudentProfile | null
  guestSession: GuestSession | null
  isLoading: boolean
  signUp: (email: string, password: string, displayName: string) => Promise<void>
  signIn: (email: string, password: string) => Promise<void>
  signOut: () => Promise<void>
  startGuestSession: (displayName: string) => void
  setActiveChild: (child: StudentProfile) => void
  addChild: (displayName: string, username: string, age: number) => Promise<StudentProfile>
  refreshChildren: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children: reactChildren }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [parentAccount, setParentAccount] = useState<ParentAccount | null>(null)
  const [studentProfiles, setStudentProfiles] = useState<StudentProfile[]>([])
  const [activeChild, setActiveChildState] = useState<StudentProfile | null>(null)
  const [guestSession, setGuestSession] = useState<GuestSession | null>(() => {
    try {
      const saved = localStorage.getItem('adeline_guest')
      return saved ? JSON.parse(saved) : null
    } catch { return null }
  })
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
      if (session) loadParentData(session.user.id)
      else setIsLoading(false)
    })

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session)
      if (session) loadParentData(session.user.id)
      else {
        setParentAccount(null)
        setStudentProfiles([])
        setActiveChildState(null)
      }
    })

    return () => subscription.unsubscribe()
  }, [])

  async function loadParentData(userId: string) {
    const { data: parent } = await supabase
      .from('parent_accounts')
      .select('*')
      .eq('id', userId)
      .single()
    setParentAccount(parent)
    await loadChildren(userId)
    setIsLoading(false)
  }

  async function loadChildren(parentId: string) {
    const { data } = await supabase
      .from('student_profiles')
      .select('*')
      .eq('parent_id', parentId)
      .order('created_at')
    setStudentProfiles(data || [])
  }

  async function refreshChildren() {
    if (!session) return
    await loadChildren(session.user.id)
  }

  async function signUp(email: string, password: string, displayName: string) {
    const { data, error } = await supabase.auth.signUp({ email, password })
    if (error) throw error
    if (data.user) {
      const { error: insertError } = await supabase.from('parent_accounts').insert({
        id: data.user.id,
        email,
        display_name: displayName
      })
      if (insertError) throw insertError
    }
  }

  async function signIn(email: string, password: string) {
    const { error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) throw error
  }

  async function signOut() {
    await supabase.auth.signOut()
    setGuestSession(null)
    localStorage.removeItem('adeline_guest')
    localStorage.removeItem('adeline_active_child')
  }

  function startGuestSession(displayName: string) {
    const guest: GuestSession = { mode: 'guest', displayName, avatarData: {}, xp: 0, adeCoins: 0 }
    setGuestSession(guest)
    localStorage.setItem('adeline_guest', JSON.stringify(guest))
  }

  function setActiveChild(child: StudentProfile) {
    setActiveChildState(child)
    localStorage.setItem('adeline_active_child', child.id)
  }

  async function addChild(displayName: string, username: string, age: number): Promise<StudentProfile> {
    if (!session) throw new Error('Not authenticated')
    const { data, error } = await supabase
      .from('student_profiles')
      .insert({ parent_id: session.user.id, display_name: displayName, username, age })
      .select()
      .single()
    if (error) throw error
    await refreshChildren()
    return data
  }

  return (
    <AuthContext.Provider value={{
      session,
      parentAccount,
      children: studentProfiles,
      activeChild,
      guestSession,
      isLoading,
      signUp,
      signIn,
      signOut,
      startGuestSession,
      setActiveChild,
      addChild,
      refreshChildren
    }}>
      {reactChildren}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
```

- [ ] **Step 2: Commit**

```bash
git add src/context/AuthContext.tsx
git commit -m "feat: add AuthContext with parent/child/guest session management"
```

---

## Task 6: Landing Page

**Files:**
- Create: `src/pages/LandingPage.tsx`

- [ ] **Step 1: Create `src/pages/LandingPage.tsx`**

```typescript
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Sparkles } from 'lucide-react'

export default function LandingPage() {
  const { startGuestSession } = useAuth()
  const navigate = useNavigate()
  const [guestName, setGuestName] = useState('')
  const [showGuestInput, setShowGuestInput] = useState(false)

  function handleGuestPlay() {
    if (!showGuestInput) { setShowGuestInput(true); return }
    if (!guestName.trim()) return
    startGuestSession(guestName.trim())
    navigate('/game')
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-50 to-amber-100 flex flex-col items-center justify-center p-6">
      <div className="w-full max-w-md bg-white rounded-3xl shadow-xl p-8 space-y-6">
        <div className="text-center space-y-2">
          <div className="w-20 h-20 bg-amber-100 rounded-2xl flex items-center justify-center mx-auto">
            <Sparkles className="w-10 h-10 text-amber-600" />
          </div>
          <h1 className="text-3xl font-bold font-serif text-slate-800">Adeline World</h1>
          <p className="text-slate-500 text-sm">Learn. Build. Explore. Graduate.</p>
        </div>

        <div className="space-y-3">
          <button
            onClick={() => navigate('/login')}
            className="w-full py-3 px-4 bg-amber-600 hover:bg-amber-700 text-white font-semibold rounded-xl transition-all"
          >
            Sign In
          </button>
          <button
            onClick={() => navigate('/signup')}
            className="w-full py-3 px-4 bg-white hover:bg-amber-50 border-2 border-amber-200 text-amber-800 font-semibold rounded-xl transition-all"
          >
            Create Parent Account
          </button>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-slate-200" />
            </div>
            <div className="relative flex justify-center text-xs">
              <span className="bg-white px-2 text-slate-400">or</span>
            </div>
          </div>

          {showGuestInput ? (
            <div className="space-y-2">
              <input
                type="text"
                placeholder="What's your name?"
                value={guestName}
                onChange={e => setGuestName(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleGuestPlay()}
                className="w-full px-4 py-3 border border-slate-200 rounded-xl text-sm focus:outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-100"
                autoFocus
              />
              <button
                onClick={handleGuestPlay}
                disabled={!guestName.trim()}
                className="w-full py-3 px-4 bg-slate-100 hover:bg-slate-200 disabled:opacity-50 text-slate-700 font-semibold rounded-xl transition-all"
              >
                Play as Guest →
              </button>
              <p className="text-xs text-slate-400 text-center">
                Guest progress saves in this browser only
              </p>
            </div>
          ) : (
            <button
              onClick={handleGuestPlay}
              className="w-full py-3 px-4 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-xl transition-all"
            >
              Play as Guest (No Account Needed)
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add src/pages/LandingPage.tsx
git commit -m "feat: add LandingPage with sign-in, signup, and guest entry"
```

---

## Task 7: Login Page

**Files:**
- Create: `src/pages/LoginPage.tsx`

- [ ] **Step 1: Create `src/pages/LoginPage.tsx`**

```typescript
import { useState, FormEvent } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { ArrowLeft } from 'lucide-react'

export default function LoginPage() {
  const { signIn } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    setIsLoading(true)
    try {
      await signIn(email, password)
      navigate('/select-child')
    } catch (err: any) {
      setError(err.message || 'Login failed. Check your email and password.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-50 to-amber-100 flex flex-col items-center justify-center p-6">
      <div className="w-full max-w-md bg-white rounded-3xl shadow-xl p-8 space-y-6">
        <div className="flex items-center gap-3">
          <Link to="/" className="p-2 rounded-lg hover:bg-amber-50 text-slate-500">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <h2 className="text-2xl font-bold font-serif text-slate-800">Parent Sign In</h2>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={e => setEmail(e.target.value)}
              className="w-full px-4 py-3 border border-slate-200 rounded-xl text-sm focus:outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-100"
              placeholder="your@email.com"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full px-4 py-3 border border-slate-200 rounded-xl text-sm focus:outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-100"
              placeholder="••••••••"
            />
          </div>

          {error && (
            <p className="text-sm text-red-600 bg-red-50 px-4 py-2 rounded-lg">{error}</p>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-3 bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white font-semibold rounded-xl transition-all"
          >
            {isLoading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        <p className="text-center text-sm text-slate-500">
          No account?{' '}
          <Link to="/signup" className="text-amber-700 font-semibold hover:underline">
            Create one
          </Link>
        </p>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add src/pages/LoginPage.tsx
git commit -m "feat: add LoginPage with email/password auth"
```

---

## Task 8: Signup Page

**Files:**
- Create: `src/pages/SignupPage.tsx`

- [ ] **Step 1: Create `src/pages/SignupPage.tsx`**

```typescript
import { useState, FormEvent } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { ArrowLeft } from 'lucide-react'

export default function SignupPage() {
  const { signUp } = useAuth()
  const navigate = useNavigate()
  const [displayName, setDisplayName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    if (password !== confirm) { setError('Passwords do not match.'); return }
    if (password.length < 8) { setError('Password must be at least 8 characters.'); return }
    setIsLoading(true)
    try {
      await signUp(email, password, displayName)
      navigate('/create-child')
    } catch (err: any) {
      setError(err.message || 'Signup failed. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-50 to-amber-100 flex flex-col items-center justify-center p-6">
      <div className="w-full max-w-md bg-white rounded-3xl shadow-xl p-8 space-y-6">
        <div className="flex items-center gap-3">
          <Link to="/" className="p-2 rounded-lg hover:bg-amber-50 text-slate-500">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h2 className="text-2xl font-bold font-serif text-slate-800">Create Parent Account</h2>
            <p className="text-xs text-slate-500 mt-0.5">You'll add your kids after signing up</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Your Name</label>
            <input
              type="text"
              required
              value={displayName}
              onChange={e => setDisplayName(e.target.value)}
              className="w-full px-4 py-3 border border-slate-200 rounded-xl text-sm focus:outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-100"
              placeholder="Mom / Dad / Guardian name"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={e => setEmail(e.target.value)}
              className="w-full px-4 py-3 border border-slate-200 rounded-xl text-sm focus:outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-100"
              placeholder="your@email.com"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full px-4 py-3 border border-slate-200 rounded-xl text-sm focus:outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-100"
              placeholder="At least 8 characters"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Confirm Password</label>
            <input
              type="password"
              required
              value={confirm}
              onChange={e => setConfirm(e.target.value)}
              className="w-full px-4 py-3 border border-slate-200 rounded-xl text-sm focus:outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-100"
              placeholder="••••••••"
            />
          </div>

          {error && (
            <p className="text-sm text-red-600 bg-red-50 px-4 py-2 rounded-lg">{error}</p>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-3 bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white font-semibold rounded-xl transition-all"
          >
            {isLoading ? 'Creating account...' : 'Create Account →'}
          </button>
        </form>

        <p className="text-center text-sm text-slate-500">
          Already have an account?{' '}
          <Link to="/login" className="text-amber-700 font-semibold hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add src/pages/SignupPage.tsx
git commit -m "feat: add SignupPage for parent account creation"
```

---

## Task 9: Create Child Page

**Files:**
- Create: `src/pages/CreateChildPage.tsx`

- [ ] **Step 1: Create `src/pages/CreateChildPage.tsx`**

```typescript
import { useState, FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { User, Plus } from 'lucide-react'

export default function CreateChildPage() {
  const { addChild, setActiveChild, children } = useAuth()
  const navigate = useNavigate()
  const [displayName, setDisplayName] = useState('')
  const [username, setUsername] = useState('')
  const [age, setAge] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  function sanitizeUsername(val: string) {
    return val.toLowerCase().replace(/[^a-z0-9_]/g, '').slice(0, 20)
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    if (username.length < 3) { setError('Username must be at least 3 characters.'); return }
    setIsLoading(true)
    try {
      const child = await addChild(displayName.trim(), username, parseInt(age) || 10)
      setActiveChild(child)
      navigate('/game')
    } catch (err: any) {
      if (err.message?.includes('unique')) {
        setError('That username is already taken. Try another one.')
      } else {
        setError(err.message || 'Could not create profile. Please try again.')
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-50 to-amber-100 flex flex-col items-center justify-center p-6">
      <div className="w-full max-w-md bg-white rounded-3xl shadow-xl p-8 space-y-6">
        <div className="text-center space-y-2">
          <div className="w-16 h-16 bg-amber-100 rounded-2xl flex items-center justify-center mx-auto">
            <User className="w-8 h-8 text-amber-600" />
          </div>
          <h2 className="text-2xl font-bold font-serif text-slate-800">Add Your First Kid</h2>
          <p className="text-sm text-slate-500">You can add more kids from the parent dashboard later</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Kid's Name</label>
            <input
              type="text"
              required
              value={displayName}
              onChange={e => setDisplayName(e.target.value)}
              className="w-full px-4 py-3 border border-slate-200 rounded-xl text-sm focus:outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-100"
              placeholder="First name or nickname"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Username <span className="text-slate-400 font-normal">(shown to other players)</span>
            </label>
            <input
              type="text"
              required
              value={username}
              onChange={e => setUsername(sanitizeUsername(e.target.value))}
              className="w-full px-4 py-3 border border-slate-200 rounded-xl text-sm focus:outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-100 font-mono"
              placeholder="coolkid_123"
              maxLength={20}
            />
            <p className="text-xs text-slate-400 mt-1">Letters, numbers, underscores only. You approve this before it goes live.</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Age</label>
            <input
              type="number"
              required
              min={4}
              max={18}
              value={age}
              onChange={e => setAge(e.target.value)}
              className="w-full px-4 py-3 border border-slate-200 rounded-xl text-sm focus:outline-none focus:border-amber-400 focus:ring-2 focus:ring-amber-100"
              placeholder="10"
            />
          </div>

          {error && (
            <p className="text-sm text-red-600 bg-red-50 px-4 py-2 rounded-lg">{error}</p>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-3 bg-amber-600 hover:bg-amber-700 disabled:opacity-50 text-white font-semibold rounded-xl transition-all flex items-center justify-center gap-2"
          >
            <Plus className="w-4 h-4" />
            {isLoading ? 'Creating...' : 'Create Profile & Enter World'}
          </button>
        </form>

        {children.length > 0 && (
          <button
            onClick={() => navigate('/select-child')}
            className="w-full py-2 text-sm text-slate-500 hover:text-slate-700"
          >
            Skip — choose an existing profile instead
          </button>
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add src/pages/CreateChildPage.tsx
git commit -m "feat: add CreateChildPage for adding child profiles"
```

---

## Task 10: Child Select Page

**Files:**
- Create: `src/pages/ChildSelectPage.tsx`

- [ ] **Step 1: Create `src/pages/ChildSelectPage.tsx`**

```typescript
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Plus, LogOut, User } from 'lucide-react'

export default function ChildSelectPage() {
  const { children, setActiveChild, signOut, parentAccount } = useAuth()
  const navigate = useNavigate()

  function selectChild(child: typeof children[0]) {
    setActiveChild(child)
    navigate('/game')
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-amber-50 to-amber-100 flex flex-col items-center justify-center p-6">
      <div className="w-full max-w-md bg-white rounded-3xl shadow-xl p-8 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold font-serif text-slate-800">Who's playing?</h2>
            <p className="text-sm text-slate-500 mt-0.5">Hi {parentAccount?.display_name} 👋</p>
          </div>
          <button
            onClick={signOut}
            className="p-2 rounded-lg hover:bg-slate-100 text-slate-400"
            title="Sign out"
          >
            <LogOut className="w-5 h-5" />
          </button>
        </div>

        {children.length === 0 ? (
          <div className="text-center py-8 text-slate-400">
            <p className="text-sm">No kids added yet.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {children.map(child => (
              <button
                key={child.id}
                onClick={() => selectChild(child)}
                className="w-full flex items-center gap-4 p-4 bg-amber-50 hover:bg-amber-100 border border-amber-200 rounded-2xl transition-all text-left"
              >
                <div className="w-12 h-12 bg-amber-200 rounded-xl flex items-center justify-center">
                  <User className="w-6 h-6 text-amber-700" />
                </div>
                <div>
                  <p className="font-semibold text-slate-800">{child.display_name}</p>
                  <p className="text-xs text-slate-500">@{child.username} · {child.xp} XP · {child.ade_coins} AdeCoins</p>
                </div>
              </button>
            ))}
          </div>
        )}

        <button
          onClick={() => navigate('/create-child')}
          className="w-full py-3 border-2 border-dashed border-amber-200 hover:border-amber-400 text-amber-700 font-semibold rounded-2xl transition-all flex items-center justify-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Add Another Kid
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add src/pages/ChildSelectPage.tsx
git commit -m "feat: add ChildSelectPage for multi-kid family switching"
```

---

## Task 11: Game Shell (Protected Placeholder)

**Files:**
- Create: `src/pages/GameShell.tsx`

- [ ] **Step 1: Create `src/pages/GameShell.tsx`**

This is a placeholder that confirms auth works. Plan 2 builds the real game here.

```typescript
import { useAuth } from '../context/AuthContext'
import { useNavigate } from 'react-router-dom'
import { LogOut, Sparkles } from 'lucide-react'

export default function GameShell() {
  const { activeChild, guestSession, signOut, parentAccount } = useAuth()
  const navigate = useNavigate()

  const playerName = activeChild?.display_name || guestSession?.displayName || 'Explorer'
  const isGuest = !!guestSession && !activeChild

  async function handleSignOut() {
    await signOut()
    navigate('/')
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-900 via-emerald-800 to-teal-900 flex flex-col items-center justify-center p-6 text-white">
      <div className="text-center space-y-6 max-w-md">
        <div className="w-20 h-20 bg-amber-400 rounded-2xl flex items-center justify-center mx-auto shadow-xl">
          <Sparkles className="w-10 h-10 text-amber-900" />
        </div>

        <div>
          <h1 className="text-3xl font-bold font-serif">Welcome to Adeline World</h1>
          <p className="text-emerald-300 mt-2">
            Hello, <span className="text-amber-300 font-semibold">{playerName}</span>!
            {isGuest && <span className="text-xs ml-2 bg-white/10 px-2 py-0.5 rounded-full">Guest</span>}
          </p>
        </div>

        <div className="bg-white/10 rounded-2xl p-6 space-y-2 text-sm text-left">
          <p className="text-emerald-300 font-semibold text-xs uppercase tracking-wider">Auth Status ✓</p>
          {activeChild && (
            <>
              <p>Player: {activeChild.display_name} (@{activeChild.username})</p>
              <p>XP: {activeChild.xp} · AdeCoins: {activeChild.ade_coins}</p>
              <p>Parent: {parentAccount?.display_name}</p>
            </>
          )}
          {isGuest && (
            <>
              <p>Guest mode — progress saved locally</p>
              <p className="text-amber-300">Create an account to save to cloud & make friends!</p>
            </>
          )}
          <p className="text-emerald-400 text-xs mt-4">
            ✓ Foundation complete — game world coming in Plan 2
          </p>
        </div>

        <button
          onClick={handleSignOut}
          className="flex items-center gap-2 px-6 py-3 bg-white/10 hover:bg-white/20 rounded-xl transition-all mx-auto"
        >
          <LogOut className="w-4 h-4" />
          {isGuest ? 'Leave Game' : 'Sign Out'}
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add src/pages/GameShell.tsx
git commit -m "feat: add GameShell placeholder - foundation auth complete"
```

---

## Task 12: Wire Up React Router in App.tsx

**Files:**
- Modify: `src/App.tsx`
- Modify: `src/main.tsx`

- [ ] **Step 1: Replace `src/App.tsx` with router**

Replace the entire contents of `src/App.tsx`:

```typescript
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import LandingPage from './pages/LandingPage'
import LoginPage from './pages/LoginPage'
import SignupPage from './pages/SignupPage'
import CreateChildPage from './pages/CreateChildPage'
import ChildSelectPage from './pages/ChildSelectPage'
import GameShell from './pages/GameShell'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { session, guestSession, activeChild, isLoading } = useAuth()
  if (isLoading) return (
    <div className="min-h-screen flex items-center justify-center bg-amber-50">
      <div className="w-8 h-8 border-4 border-amber-400 border-t-transparent rounded-full animate-spin" />
    </div>
  )
  const isLoggedIn = (session && activeChild) || guestSession
  return isLoggedIn ? <>{children}</> : <Navigate to="/" replace />
}

function RequireParent({ children }: { children: React.ReactNode }) {
  const { session, isLoading } = useAuth()
  if (isLoading) return null
  return session ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/select-child" element={
          <RequireParent><ChildSelectPage /></RequireParent>
        } />
        <Route path="/create-child" element={
          <RequireParent><CreateChildPage /></RequireParent>
        } />
        <Route path="/game" element={
          <RequireAuth><GameShell /></RequireAuth>
        } />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
```

- [ ] **Step 2: Wrap app with AuthProvider in `src/main.tsx`**

Replace `src/main.tsx`:

```typescript
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { AuthProvider } from './context/AuthContext.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AuthProvider>
      <App />
    </AuthProvider>
  </StrictMode>,
)
```

- [ ] **Step 3: Commit**

```bash
git add src/App.tsx src/main.tsx
git commit -m "feat: wire up React Router with auth guards - foundation complete"
```

---

## Task 13: End-to-End Smoke Test

- [ ] **Step 1: Start the dev server**

```bash
npm run dev
```

Expected: `Server running on http://0.0.0.0:3000`

- [ ] **Step 2: Test guest flow**

1. Open http://localhost:3000
2. Should see LandingPage with 3 buttons
3. Click "Play as Guest" → enter a name → click "Play as Guest →"
4. Should redirect to `/game` and show GameShell with guest name
5. Click "Leave Game" → back to LandingPage ✓

- [ ] **Step 3: Test parent signup flow**

1. Click "Create Parent Account"
2. Fill in name, email, password (8+ chars), confirm → Submit
3. Should redirect to `/create-child`
4. Fill in child name, username, age → Submit
5. Should redirect to `/game` showing child name + XP/coins
6. Click "Sign Out" → back to LandingPage ✓

- [ ] **Step 4: Test parent login flow**

1. Click "Sign In"
2. Enter same email/password → Submit
3. Should redirect to `/select-child` showing the child profile
4. Click child → redirects to `/game` ✓

- [ ] **Step 5: Test auth guard**

1. Sign out, then go directly to http://localhost:3000/game
2. Should redirect to `/` ✓

- [ ] **Step 6: Verify in Supabase dashboard**

Go to https://supabase.com/dashboard/project/gyxowttfwqbajoapfebf/editor

Run:
```sql
select * from parent_accounts;
select * from student_profiles;
```
Expected: Your test parent and child rows appear ✓

- [ ] **Step 7: Final commit**

```bash
git add -A
git commit -m "test: foundation smoke test complete - auth flows verified"
git push origin main
```

---

## What's Next

**Plan 2: Avatar & World** builds on this foundation:
- Avatar builder (layered character customization)
- Adeline NPC sprite from `adeline_portrait.png`
- 2D Hub world (CSS/SVG top-down view)
- Math Mines room
- Story Forest room
- In-game HUD (player name, XP bar, AdeCoins)
