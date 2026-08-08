import { NextRequest } from 'next/server'

export const dynamic = 'force-dynamic'

function backendBase() {
  return (
    process.env.BRAIN_INTERNAL_URL ||
    process.env.BRAIN_URL ||
    process.env.NEXT_PUBLIC_BRAIN_URL ||
    'https://dearadeline-withlove-production.up.railway.app'
  ).replace(/\/$/, '')
}

export async function POST(request: NextRequest) {
  const body = await request.text()
  const authorization = request.headers.get('authorization') || ''
  const base = backendBase()

  // Railway has supported both mounts over the life of the app. Trying both
  // keeps Vercel previews usable while the Brain service catches up to a branch.
  const candidates = [
    `${base}/brain/conversation/stream`,
    `${base}/conversation/stream`,
  ]

  let lastStatus = 502
  let lastMessage = 'Adeline could not reach her Brain.'

  for (const url of candidates) {
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(authorization ? { Authorization: authorization } : {}),
        },
        body,
        cache: 'no-store',
      })

      if (response.ok && response.body) {
        return new Response(response.body, {
          status: 200,
          headers: {
            'Content-Type': response.headers.get('content-type') || 'text/event-stream',
            'Cache-Control': 'no-cache, no-transform',
            'X-Accel-Buffering': 'no',
          },
        })
      }

      lastStatus = response.status
      lastMessage = await response.text().catch(() => `Brain returned ${response.status}`)

      // Auth errors will be identical on both mounts, so don't make a duplicate request.
      if (response.status === 401 || response.status === 403 || response.status === 422) break
    } catch (error) {
      lastMessage = error instanceof Error ? error.message : 'Brain connection failed.'
    }
  }

  return Response.json(
    { error: lastMessage || 'Adeline could not reach her Brain.' },
    { status: lastStatus >= 400 ? lastStatus : 502 },
  )
}
