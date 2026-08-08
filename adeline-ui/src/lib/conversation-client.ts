import { supabase } from '@/lib/supabase'
import type { ConversationEvent, ConversationMessage, Track } from '@/lib/brain-client'

async function authHeaders(): Promise<Record<string, string>> {
  try {
    const { data } = await supabase.auth.getSession()
    const token = data.session?.access_token
    return token ? { Authorization: `Bearer ${token}` } : {}
  } catch {
    return {}
  }
}

export async function* streamAdelineConversation(params: {
  studentId: string
  message: string
  track?: Track
  gradeLevel: string
  history: ConversationMessage[]
}): AsyncGenerator<ConversationEvent> {
  const response = await fetch('/api/adeline/conversation', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(await authHeaders()),
    },
    body: JSON.stringify({
      student_id: params.studentId,
      message: params.message,
      track: params.track ?? null,
      grade_level: params.gradeLevel,
      conversation_history: params.history.map((message) => ({
        role: message.role === 'adeline' ? 'assistant' : 'user',
        content: message.content,
      })),
    }),
    cache: 'no-store',
  })

  if (!response.ok || !response.body) {
    let detail = `HTTP ${response.status}`
    try {
      const data = await response.json() as { error?: string }
      if (data.error) detail = data.error
    } catch {
      // keep HTTP fallback
    }
    yield { type: 'error', message: detail }
    return
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let currentEvent = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''

    for (const line of lines) {
      if (line.startsWith('event: ')) {
        currentEvent = line.slice(7).trim()
        continue
      }
      if (!line.startsWith('data: ')) continue

      const raw = line.slice(6).trim()
      if (!raw) continue

      try {
        const payload = JSON.parse(raw)
        if (currentEvent === 'text') yield { type: 'text', delta: payload.delta ?? '' }
        else if (currentEvent === 'block') yield { type: 'block', ...payload }
        else if (currentEvent === 'zpd') yield { type: 'zpd', ...payload }
        else if (currentEvent === 'done') yield { type: 'done' }
        else if (currentEvent === 'error') yield { type: 'error', message: payload.message ?? 'Adeline lost the thread.' }
      } catch {
        // Ignore malformed partial SSE frames.
      }
      currentEvent = ''
    }
  }
}
