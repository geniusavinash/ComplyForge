import axios from 'axios'

export const API_BASE_URL = 'http://localhost:8000'

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

export async function analyze(agentDescriptor) {
  const { data } = await api.post('/api/analyze', agentDescriptor)
  return data
}

export async function getSampleAgents() {
  const { data } = await api.get('/api/sample-agents')
  return data
}

export async function getEnforcementEvents(limit = 100) {
  const { data } = await api.get('/api/enforcement/events', {
    params: { limit },
  })
  return data
}

/**
 * POST /api/deploy-policy/{slug}
 * @param {string} slug
 * @param {string} [policyYaml] - optional explicit YAML override
 * @returns {Promise<{deployed:boolean, policy_path:string, reload_method:string,
 *                    reload_note?:string, rule_count:number, agent_slug:string}>}
 */
export async function deployPolicy(slug, policyYaml) {
  const body = policyYaml ? { policy_yaml: policyYaml } : {}
  const { data } = await api.post(
    `/api/deploy-policy/${encodeURIComponent(slug)}`,
    body,
  )
  return data
}

/**
 * GET /api/inventory/zip
 * Triggers the browser to download the bundled inventory zip.
 */
export function getInventoryZipUrl() {
  return `${API_BASE_URL}/api/inventory/zip`
}

export function getPdfUrl(filename) {
  return `${API_BASE_URL}/api/pdf/${encodeURIComponent(filename)}`
}

/**
 * POST /api/extract-descriptor (multipart)
 *
 * Accepts image/png, image/jpeg, or application/pdf and returns the
 * AgentDescriptor JSON that Gemini Vision extracted from the document.
 *
 * @param {File} file
 * @returns {Promise<object>} AgentDescriptor
 */
export async function extractDescriptor(file) {
  if (!file) throw new Error('extractDescriptor: file is required')
  const form = new FormData()
  form.append('file', file, file.name || 'upload')

  const response = await fetch(`${API_BASE_URL}/api/extract-descriptor`, {
    method: 'POST',
    body: form,
  })

  if (!response.ok) {
    let detail = ''
    try {
      const body = await response.json()
      detail = body?.detail || body?.error || ''
    } catch {
      try {
        detail = await response.text()
      } catch {
        detail = ''
      }
    }
    const suffix = detail ? ` — ${detail}` : ''
    throw new Error(
      `extract-descriptor failed: ${response.status} ${response.statusText}${suffix}`,
    )
  }

  return response.json()
}

/**
 * Stream Server-Sent Events from POST /api/analyze/stream.
 *
 * EventSource cannot be used because it does not support POST bodies; we use
 * fetch + ReadableStream + a manual SSE parser instead.
 *
 * @param {object} agentDescriptor - body for /api/analyze/stream
 * @param {(event: {step?: string, status?: string, payload?: any}) => void} onEvent
 * @param {() => void} [onDone]
 * @param {(err: Error) => void} [onError]
 * @returns {AbortController} cancel by calling controller.abort()
 */
export function streamAnalyze(agentDescriptor, onEvent, onDone, onError) {
  const controller = new AbortController()

  ;(async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/analyze/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
        },
        body: JSON.stringify(agentDescriptor),
        signal: controller.signal,
      })

      if (!response.ok || !response.body) {
        throw new Error(`stream request failed: ${response.status}`)
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''

      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        // SSE messages are separated by a blank line.
        let sepIndex
        while ((sepIndex = buffer.indexOf('\n\n')) !== -1) {
          const rawEvent = buffer.slice(0, sepIndex)
          buffer = buffer.slice(sepIndex + 2)
          const dataLines = rawEvent
            .split('\n')
            .filter((line) => line.startsWith('data:'))
            .map((line) => line.slice(5).trimStart())

          if (dataLines.length === 0) continue
          const dataStr = dataLines.join('\n')
          if (!dataStr) continue

          let parsed
          try {
            parsed = JSON.parse(dataStr)
          } catch {
            parsed = { raw: dataStr }
          }
          onEvent && onEvent(parsed)
        }
      }

      onDone && onDone()
    } catch (err) {
      if (err.name === 'AbortError') return
      onError && onError(err)
    }
  })()

  return controller
}
