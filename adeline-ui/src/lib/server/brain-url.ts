/**
 * Server-side Brain origin. Docker compose uses BRAIN_INTERNAL_URL=http://adeline-brain:8000.
 * Vercel is outside that network — if that hostname wins, every login and /brain proxy
 * 404s with a generic {message, requestId} body. On Vercel only a public Railway origin
 * is reachable.
 */
export const PUBLIC_BRAIN_URL = 'https://dearadeline-withlove-production.up.railway.app';

function normalize(raw: string): string {
  return raw.trim().replace(/\/$/, '').replace(/\/brain$/i, '');
}

function usableBrainOrigin(raw: string, onVercel: boolean): string | null {
  const origin = normalize(raw);
  if (!origin) return null;
  let url: URL;
  try {
    url = new URL(origin);
  } catch {
    return null;
  }
  if (url.protocol !== 'http:' && url.protocol !== 'https:') return null;
  const host = url.hostname;
  if (host === 'dearadeline.co' || host === 'www.dearadeline.co' || host.endsWith('.vercel.app')) {
    return null;
  }
  if (onVercel && !host.endsWith('.up.railway.app')) {
    return null;
  }
  return origin;
}

export function resolveBrainBaseUrl(): string {
  const onVercel = Boolean(process.env.VERCEL);
  for (const raw of [
    process.env.BRAIN_INTERNAL_URL,
    process.env.BRAIN_URL,
    process.env.NEXT_PUBLIC_BRAIN_URL,
  ]) {
    if (!raw) continue;
    const origin = usableBrainOrigin(raw, onVercel);
    if (origin) return origin;
  }
  return PUBLIC_BRAIN_URL;
}
