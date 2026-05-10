import { createBrowserClient } from '@supabase/ssr'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL ?? 'https://dummy.supabase.co'
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? 'dummy-anon-key'

// createBrowserClient stores auth in cookies (in addition to localStorage),
// enabling the Next.js middleware and server components to read the session.
export const supabase = createBrowserClient(supabaseUrl, supabaseAnonKey)
