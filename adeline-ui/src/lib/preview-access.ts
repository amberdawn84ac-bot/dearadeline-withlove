export function isPreviewDeployment(): boolean {
  if (typeof window === 'undefined') return false

  const host = window.location.hostname.toLowerCase()
  return host.endsWith('.vercel.app') || host === 'localhost' || host === '127.0.0.1'
}
